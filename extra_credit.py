"""
extra_credit.py - Extended multi-agent system for Beaver's Choice Paper Company.

Three additional features built on top of project_starter.py:

1. Customer Negotiation Agent
   A per-request LLM agent that plays the customer role using the CSV context
   (job title, mood, event type, order size).  It sends requests to the company
   orchestrator through a tool, evaluates the response, and negotiates up to two
   rounds before accepting the best available deal.

2. Animated Terminal Display
   Runs the company orchestrator in a background thread while capturing its output.
   After each request completes, a colour-coded step-by-step replay shows which
   agent called which tool, wrapped in Rich panels that surface the customer context
   and the final response.

3. Business Advisor Agent
   Runs once after all requests are processed.  Queries the SQLite database with
   four analysis tools (revenue by item, stockout incidents, cash flow trend,
   discount impact) and returns prioritised, actionable recommendations.
"""

import io
import json
import re
import sys
import threading
import time

import dotenv
import os
import pandas as pd
from sqlalchemy.sql import text as sql_text

from rich.console import Console
from rich.live import Live
from rich.panel import Panel
from rich.table import Table
from rich.text import Text

import project_starter as ps
from project_starter import (
    CATALOG_PRICES,
    db_engine,
    generate_financial_report,
    init_database,
)
from smolagents import OpenAIServerModel, ToolCallingAgent, tool

console = Console(file=sys.__stdout__, highlight=False)


# -------------------------------------------------------------
# SHARED LLM MODEL
# -------------------------------------------------------------

_model: "OpenAIServerModel | None" = None


def _get_model() -> OpenAIServerModel:
    global _model
    if _model is None:
        dotenv.load_dotenv()
        _model = OpenAIServerModel(
            model_id=os.getenv("OPENAI_MODEL", "gpt-4o-mini"),
            api_base=os.getenv("OPENAI_API_BASE", "https://openai.vocareum.com/v1"),
            api_key=os.getenv("UDACITY_OPENAI_API_KEY") or os.getenv("OPENAI_API_KEY"),
        )
    return _model


# -------------------------------------------------------------
# FEATURE 2 - ANIMATED TERMINAL DISPLAY
# -------------------------------------------------------------

# Map tool names to the agent that owns them and a display colour.
_TOOL_AGENT_MAP = {
    "list_catalog_items":       ("[Inv] Inventory",    "blue"),
    "check_item_stock":         ("[Inv] Inventory",    "blue"),
    "list_available_inventory": ("[Inv] Inventory",    "blue"),
    "place_supplier_restock":   ("[Inv] Inventory",    "blue"),
    "restock_all_low_inventory":("[Inv] Inventory",    "blue"),
    "calculate_quote":          ("[Quo] Quoting",      "magenta"),
    "search_historical_quotes": ("[Quo] Quoting",      "magenta"),
    "process_sale_transaction": ("[OK] Sales",         "green"),
    "get_current_cash_balance": ("[OK] Sales",         "green"),
    "inventory_agent":          ("[Orch] Orchestrator", "cyan"),
    "quoting_agent":            ("[Orch] Orchestrator", "cyan"),
    "sales_agent":              ("[Orch] Orchestrator", "cyan"),
    "query_paper_company":      ("[Cust] Customer",     "yellow"),
}

_MOOD_COLOUR = {
    "stressed":    "yellow3",
    "pissed off":  "red",
    "excited":     "bright_green",
    "happy":       "green",
    "calm":        "cyan",
    "neutral":     "white",
    "worried":     "yellow",
    "anxious":     "yellow",
    "satisfied":   "green",
}


def _mood_colour(mood: str) -> str:
    return _MOOD_COLOUR.get(mood.lower().strip(), "white")


class _LiveCapture:
    """
    Writable stream that both buffers all text and tracks the most recently
    called tool/agent in real time (thread-safe).  Passed as sys.stdout inside
    the company-orchestrator background thread so the spinner can read live state.
    """

    def __init__(self) -> None:
        self._buf: list[str] = []
        self._lock = threading.Lock()
        self.last_tool: str = ""
        self.last_agent: str = "Orchestrator"
        self.last_colour: str = "cyan"

    def write(self, text: str) -> int:
        with self._lock:
            self._buf.append(text)
            for match in re.finditer(r"Calling tool: '([^']+)'", text):
                name = match.group(1)
                agent_label, colour = _TOOL_AGENT_MAP.get(name, ("[Tool] Agent", "white"))
                self.last_tool = name
                self.last_agent = agent_label
                self.last_colour = colour
        return len(text)

    def flush(self) -> None:
        pass

    def getvalue(self) -> str:
        with self._lock:
            return "".join(self._buf)


def _parse_tool_calls(raw: str) -> list[tuple[str, str, str]]:
    """
    Extract tool calls from captured smolagents stdout.

    Returns a list of (tool_name, agent_label, colour) tuples.
    """
    calls = []
    # smolagents prints lines like:
    #   Calling tool: 'check_item_stock' with arguments: {...}
    for match in re.finditer(r"Calling tool: '([^']+)'", raw):
        name = match.group(1)
        agent_label, colour = _TOOL_AGENT_MAP.get(name, ("[Tool] Agent", "white"))
        calls.append((name, agent_label, colour))
    return calls


def animated_handle_request(request: str, context: dict) -> str:
    """
    Run the company orchestrator in a background thread while displaying a
    live Rich animation.  Returns the company's response string.
    """
    result_box: list[str] = []
    capture = _LiveCapture()

    def _run() -> None:
        old_stdout = sys.stdout
        sys.stdout = capture  # type: ignore[assignment]
        try:
            result = ps.handle_customer_request(request)
        except Exception as exc:
            result = f"Error: {exc}"
        finally:
            sys.stdout = old_stdout
        result_box.append(result)

    thread = threading.Thread(target=_run, daemon=True)
    colour = _mood_colour(context.get("mood", ""))

    # -- Customer context header ------------------------------
    console.print(Panel(
        f"[bold {colour}]{context.get('job', 'Customer')}[/] "
        f"organizing a [italic]{context.get('event', 'event')}[/]\n"
        f"Order size: {context.get('need_size', '')}",
        title="[bold][Cust] Customer Request[/bold]",
        border_style=colour,
    ))

    thread.start()
    start = time.time()

    # -- Live spinner showing current agent -------------------
    spinner_frames = ["|", "/", "-", "\\"]
    tick = 0
    with Live(console=console, refresh_per_second=8) as live:
        while thread.is_alive():
            elapsed = int(time.time() - start)
            frame = spinner_frames[tick % len(spinner_frames)]
            agent = capture.last_agent
            tool  = capture.last_tool
            col   = capture.last_colour
            if tool:
                line = (
                    f"  {frame} [{col}]{agent}[/{col}]"
                    f" calling [bold]{tool}[/bold] ... {elapsed}s"
                )
            else:
                line = f"  {frame} [cyan]Orchestrator[/cyan] routing request ... {elapsed}s"
            live.update(Text.from_markup(line))
            tick += 1
            time.sleep(0.12)
    console.print()

    thread.join()

    # -- Replay tool calls colour-coded by agent --------------
    calls = _parse_tool_calls(capture.getvalue())
    if calls:
        table = Table(show_header=True, header_style="bold dim", box=None, padding=(0, 2))
        table.add_column("#",     style="dim", width=3)
        table.add_column("Agent", width=22)
        table.add_column("Tool",  style="bold")

        for i, (tool_name, agent_label, col) in enumerate(calls, 1):
            table.add_row(str(i), f"[{col}]{agent_label}[/{col}]", tool_name)

        console.print(Panel(table, title="[*] Agent Steps", border_style="dim"))

    # -- Final response panel ---------------------------------
    result = result_box[0] if result_box else "No response received."
    console.print(Panel(
        result[:700] + ("..." if len(result) > 700 else ""),
        title="[green bold][OK] Company Response[/green bold]",
        border_style="green",
    ))

    return result


# -------------------------------------------------------------
# FEATURE 1 - CUSTOMER NEGOTIATION AGENT
# -------------------------------------------------------------

_BUDGET_MAP = {
    "small":      200,
    "medium":     600,
    "large":     2000,
    "very large": 5000,
}


def _make_company_query_tool(request_date: str, context: dict):
    """
    Return a @tool bound to a specific request date and customer context.
    Each call runs the company orchestrator with an animated Rich display.
    """
    @tool
    def query_paper_company(customer_request: str) -> str:
        """
        Send a request or counter-proposal to Beaver's Choice Paper Company
        and return their response covering availability, pricing, and order status.

        Args:
            customer_request: The request or counter-proposal text from the customer.

        Returns:
            The company's full response as a plain text string.
        """
        # Reset orchestrator so each negotiation round starts fresh
        ps._orchestrator_instance = None
        full = f"{customer_request} (Date of request: {request_date})"
        return animated_handle_request(full, context)

    return query_paper_company


def run_customer_negotiation(row: pd.Series, request_date: str) -> str:
    """
    Instantiate a customer agent for one CSV row and let it negotiate with
    the company orchestrator.  Returns the final agreed outcome.
    """
    job = str(row.get("job", "customer"))
    mood = str(row.get("mood", "neutral"))
    event = str(row.get("event", "event"))
    need_size = str(row.get("need_size", "medium"))
    original_request = str(row.get("request", row.get("response", "")))
    budget = _BUDGET_MAP.get(need_size.lower().strip(), 600)

    context = {"job": job, "mood": mood, "event": event, "need_size": need_size}
    query_tool = _make_company_query_tool(request_date, context)

    # Personality from mood
    personality_hints = {
        "stressed":   "You are under pressure - be direct and emphasise the deadline.",
        "pissed off": "You are frustrated - be firm and push hard for a better deal.",
        "excited":    "You are enthusiastic - be warm but still negotiate for value.",
        "happy":      "You are in a good mood - be friendly but sensible with money.",
        "calm":       "You are relaxed - be polite and methodical.",
    }
    personality = personality_hints.get(mood.lower().strip(), "Be professional and clear.")

    customer_agent = ToolCallingAgent(
        tools=[query_tool],
        model=_get_model(),
        name="customer_agent",
        description=f"Customer agent: {job} organising {event}",
        max_steps=6,
        instructions=(
            f"You are a {job} who needs paper supplies for an upcoming {event}. "
            f"{personality} "
            f"Your total budget is approximately ${budget}. "
            "Use query_paper_company to contact the supplier. "
            "Step 1: send your original request. "
            "Step 2: review the response. If items are unavailable, ask for the "
            "closest available alternative. If the total price exceeds your budget, "
            "politely ask for a discount or a smaller quantity. "
            "Make at most 2 queries then accept the best available offer. "
            "End with final_answer summarising what was agreed, the total cost, "
            "and the expected delivery date."
        ),
    )

    try:
        # Suppress smolagents' verbose step output from the customer agent;
        # the company orchestrator output is already captured inside animated_handle_request.
        old_stdout = sys.stdout
        sys.stdout = io.StringIO()
        try:
            result = str(customer_agent.run(
                f"Purchase paper supplies: {original_request}\n"
                f"Budget: ~${budget}. Negotiate if needed, confirm the best available deal."
            ))
        finally:
            sys.stdout = old_stdout
        return result
    except Exception as exc:
        return f"Customer negotiation error: {exc}"


# -------------------------------------------------------------
# FEATURE 3 - BUSINESS ADVISOR AGENT
# -------------------------------------------------------------

@tool
def analyze_revenue_by_item(as_of_date: str) -> str:
    """
    Return total sales revenue and units sold, ranked by highest revenue item.

    Args:
        as_of_date: Cut-off date in YYYY-MM-DD format.

    Returns:
        A formatted table of item name, units sold, and total revenue.
    """
    query = """
        SELECT item_name,
               SUM(units)  AS total_units,
               SUM(price)  AS total_revenue
        FROM transactions
        WHERE transaction_type = 'sales'
          AND transaction_date <= :d
        GROUP BY item_name
        ORDER BY total_revenue DESC
        LIMIT 20
    """
    with db_engine.connect() as conn:
        rows = conn.execute(sql_text(query), {"d": as_of_date}).fetchall()
    if not rows:
        return "No sales data found."
    lines = [f"Top revenue items as of {as_of_date}:"]
    for r in rows:
        name = str(r[0]) if r[0] is not None else "Unknown"
        lines.append(f"  {name:<35} {r[1] or 0:>6} units   ${(r[2] or 0):>8.2f}")
    return "\n".join(lines)


@tool
def analyze_stockout_incidents(as_of_date: str) -> str:
    """
    Identify catalog items that have reached zero net stock, indicating potential lost sales.

    Args:
        as_of_date: Date to evaluate stock levels, in YYYY-MM-DD format.

    Returns:
        List of zero-stock items with their minimum thresholds.
    """
    query = """
        SELECT i.item_name,
               i.min_stock_level,
               COALESCE(SUM(CASE WHEN t.transaction_type = 'stock_orders' THEN t.units ELSE 0 END), 0)
             - COALESCE(SUM(CASE WHEN t.transaction_type = 'sales'        THEN t.units ELSE 0 END), 0)
               AS net_stock
        FROM inventory i
        LEFT JOIN transactions t
               ON t.item_name = i.item_name
              AND t.transaction_date <= :d
        GROUP BY i.item_name, i.min_stock_level
        HAVING net_stock <= 0
        ORDER BY i.item_name
    """
    with db_engine.connect() as conn:
        rows = conn.execute(sql_text(query), {"d": as_of_date}).fetchall()
    if not rows:
        return f"No zero-stock items as of {as_of_date} - all items have positive stock."
    lines = [f"Zero-stock items as of {as_of_date}:"]
    for r in rows:
        name = str(r[0]) if r[0] is not None else "Unknown"
        lines.append(f"  {name:<35} net={r[2] or 0:>4}  min threshold={r[1] or 0}")
    return "\n".join(lines)


@tool
def analyze_cash_flow_trend(as_of_date: str) -> str:
    """
    Show daily cash inflows from sales versus outflows from stock orders.

    Args:
        as_of_date: End date for the analysis in YYYY-MM-DD format.

    Returns:
        Day-by-day cash flow table with net position per day.
    """
    query = """
        SELECT transaction_date,
               SUM(CASE WHEN transaction_type = 'sales'        THEN price ELSE 0 END) AS inflow,
               SUM(CASE WHEN transaction_type = 'stock_orders' THEN price ELSE 0 END) AS outflow
        FROM transactions
        WHERE transaction_date <= :d
        GROUP BY transaction_date
        ORDER BY transaction_date
    """
    with db_engine.connect() as conn:
        rows = conn.execute(sql_text(query), {"d": as_of_date}).fetchall()
    if not rows:
        return "No transaction data."
    lines = ["Date           | Sales In ($) | Stock Out ($) | Net ($)"]
    lines.append("-" * 60)
    for r in rows:
        net = r[1] - r[2]
        sign = "+" if net >= 0 else ""
        lines.append(f"{r[0]:<15}| {r[1]:>12.2f} | {r[2]:>13.2f} | {sign}{net:.2f}")
    return "\n".join(lines)


@tool
def analyze_discount_impact(as_of_date: str) -> str:
    """
    Compare actual sales revenue against full catalogue list prices to quantify
    the total discount given and its effect on margins.

    Args:
        as_of_date: End date for the analysis in YYYY-MM-DD format.

    Returns:
        Per-item discount summary plus aggregate totals.
    """
    query = """
        SELECT item_name, SUM(units) AS units, SUM(price) AS actual
        FROM transactions
        WHERE transaction_type = 'sales' AND transaction_date <= :d
        GROUP BY item_name
    """
    with db_engine.connect() as conn:
        rows = conn.execute(sql_text(query), {"d": as_of_date}).fetchall()
    if not rows:
        return "No sales data."

    total_list = 0.0
    total_actual = 0.0
    lines = ["Item                                    | List ($) | Actual ($) | Discount"]
    lines.append("-" * 75)
    for r in rows:
        list_price = CATALOG_PRICES.get(r[0], 0.0)
        units = r[1] or 0
        actual = r[2] or 0.0
        list_val = list_price * units
        discount = list_val - actual
        total_list += list_val
        total_actual += actual
        if list_val > 0:
            pct = discount / list_val * 100
            lines.append(
                f"{str(r[0]):<40}| {list_val:>8.2f} | {actual:>10.2f} | {pct:>5.1f}%"
            )

    discount_total = total_list - total_actual
    overall_pct = discount_total / total_list * 100 if total_list else 0
    lines.append("-" * 75)
    lines.append(
        f"{'TOTAL':<40}| {total_list:>8.2f} | {total_actual:>10.2f} | {overall_pct:>5.1f}%"
    )
    lines.append(f"\nTotal revenue foregone via discounts: ${discount_total:.2f}")
    return "\n".join(lines)


def build_business_advisor() -> ToolCallingAgent:
    return ToolCallingAgent(
        tools=[
            analyze_revenue_by_item,
            analyze_stockout_incidents,
            analyze_cash_flow_trend,
            analyze_discount_impact,
        ],
        model=_get_model(),
        name="business_advisor",
        description="Business advisor that analyses all transactions and recommends operational improvements.",
        max_steps=12,
        instructions=(
            "You are a senior business advisor for Beaver's Choice Paper Company. "
            "Call ALL four analysis tools to build a complete picture of the business. "
            "Then provide a structured report with: "
            "(1) Key findings from the data, "
            "(2) At least 3 specific, actionable recommendations to improve revenue and efficiency, "
            "(3) Priority order for implementing the recommendations. "
            "Be specific - reference actual item names, amounts, and percentages from the data. "
            "Always end with final_answer containing the full report."
        ),
    )


def get_business_recommendations(as_of_date: str) -> str:
    advisor = build_business_advisor()
    try:
        return str(advisor.run(
            f"Analyse all business performance up to {as_of_date}. "
            "Use all four analysis tools, then give a prioritised set of "
            "actionable recommendations to improve inventory management, "
            "pricing strategy, and overall revenue."
        ))
    except Exception as exc:
        return f"Business advisor error: {exc}"


# -------------------------------------------------------------
# ENHANCED TEST RUNNER
# -------------------------------------------------------------

def run_extra_credit_scenarios():
    """
    Enhanced test harness combining all three extra-credit features:
    - Animated Rich terminal display per request
    - Customer negotiation agent per request
    - Business advisor summary after all requests
    """
    console.print(Panel.fit(
        "[bold cyan]Beaver's Choice Paper Company[/bold cyan]\n"
        "[dim]Multi-Agent System - Extra Credit Edition[/dim]\n"
        "[dim]Customer negotiation . Animated display . Business advisor[/dim]",
        border_style="cyan",
    ))

    init_database(db_engine)

    df = pd.read_csv("quote_requests_sample.csv")
    df["request_date"] = pd.to_datetime(
        df["request_date"], format="%m/%d/%y", errors="coerce"
    )
    df.dropna(subset=["request_date"], inplace=True)
    df = df.sort_values("request_date").reset_index(drop=True)

    initial_date = df["request_date"].min().strftime("%Y-%m-%d")
    report = generate_financial_report(initial_date)
    current_cash = report["cash_balance"]
    current_inventory = report["inventory_value"]

    results = []
    for idx, row in df.iterrows():
        request_date = row["request_date"].strftime("%Y-%m-%d")
        context = {
            "job":       str(row.get("job", "customer")),
            "mood":      str(row.get("mood", "neutral")),
            "event":     str(row.get("event", "event")),
            "need_size": str(row.get("need_size", "medium")),
        }

        console.rule(
            f"[bold]Request {idx + 1}/{len(df)} - {request_date}[/bold]   "
            f"[dim]cash ${current_cash:,.0f}  inv ${current_inventory:,.0f}[/dim]"
        )

        # Reset the singleton so each request gets a fresh orchestrator state.
        ps._orchestrator_instance = None

        response = run_customer_negotiation(row, request_date)

        report = generate_financial_report(request_date)
        current_cash = report["cash_balance"]
        current_inventory = report["inventory_value"]

        console.print(
            f"[dim]  -> cash ${current_cash:,.2f}  |  inventory ${current_inventory:,.2f}[/dim]\n"
        )

        results.append({
            "request_id":      idx + 1,
            "request_date":    request_date,
            "cash_balance":    current_cash,
            "inventory_value": current_inventory,
            "response":        response,
        })

        time.sleep(0.1)

    # Save results
    pd.DataFrame(results).to_csv("test_results.csv", index=False)
    console.print(f"[green]Saved test_results.csv ({len(results)} rows)[/green]")

    # Final financial report
    final_date = df["request_date"].max().strftime("%Y-%m-%d")
    final = generate_financial_report(final_date)

    summary = Table(show_header=False, box=None, padding=(0, 2))
    summary.add_row("[bold]Final Cash[/bold]",      f"${final['cash_balance']:>12,.2f}")
    summary.add_row("[bold]Final Inventory[/bold]",  f"${final['inventory_value']:>12,.2f}")
    summary.add_row("[bold]Requests processed[/bold]", str(len(results)))
    console.print(Panel(summary, title="[Chart] Final Financial Report", border_style="blue"))

    # Business advisor
    console.rule("[bold yellow][Orch] Business Advisor[/bold yellow]")
    console.print("[dim]Running analysis - this may take a minute...[/dim]")
    advice = get_business_recommendations(final_date)
    console.print(Panel(advice, title="[Idea] Business Recommendations", border_style="yellow"))

    return results


# -------------------------------------------------------------
# SMOKE TEST (fast, no LLM)
# -------------------------------------------------------------

def _smoke_test():
    """
    Quick sanity check that does NOT call the LLM.
    Verifies: DB tools, animation parser, Rich panels.
    """
    console.print("[bold]Running smoke tests...[/bold]")

    # 1. Init DB and check tools work
    init_database(db_engine)
    result = analyze_revenue_by_item("2025-12-31")
    assert "No sales data" in result or "units" in result, f"analyze_revenue_by_item failed: {result}"
    console.print("[green]  [OK] analyze_revenue_by_item[/green]")

    result = analyze_stockout_incidents("2025-12-31")
    assert isinstance(result, str) and len(result) > 0
    console.print("[green]  [OK] analyze_stockout_incidents[/green]")

    result = analyze_cash_flow_trend("2025-12-31")
    assert isinstance(result, str)
    console.print("[green]  [OK] analyze_cash_flow_trend[/green]")

    result = analyze_discount_impact("2025-12-31")
    assert isinstance(result, str)
    console.print("[green]  [OK] analyze_discount_impact[/green]")

    # 2. Tool-call parser
    fake_output = (
        "Calling tool: 'check_item_stock' with arguments: {}\n"
        "Calling tool: 'calculate_quote' with arguments: {}\n"
        "Calling tool: 'process_sale_transaction' with arguments: {}\n"
    )
    calls = _parse_tool_calls(fake_output)
    assert len(calls) == 3
    assert calls[0][0] == "check_item_stock"
    assert calls[1][0] == "calculate_quote"
    assert calls[2][0] == "process_sale_transaction"
    console.print("[green]  [OK] _parse_tool_calls[/green]")

    # 3. Mood colour helper
    assert _mood_colour("stressed") == "yellow3"
    assert _mood_colour("unknown_mood") == "white"
    console.print("[green]  [OK] _mood_colour[/green]")

    # 4. Budget map
    assert _BUDGET_MAP["small"] == 200
    assert _BUDGET_MAP["large"] == 2000
    console.print("[green]  [OK] _BUDGET_MAP[/green]")

    # 5. Rich panel renders without error
    context = {"job": "teacher", "mood": "stressed", "event": "school fair", "need_size": "small"}
    colour = _mood_colour(context["mood"])
    console.print(Panel(
        f"{context['job']} | {context['event']} | mood: {context['mood']}",
        title="Test panel - ignore", border_style=colour,
    ))
    console.print("[green]  [OK] Rich Panel renders[/green]")

    console.print("[bold green]All smoke tests passed.[/bold green]")


if __name__ == "__main__":
    import sys
    if len(sys.argv) > 1 and sys.argv[1] == "--smoke":
        _smoke_test()
    else:
        run_extra_credit_scenarios()
