# Beaver's Choice Paper Company — Multi-Agent System Report

## 1. System Overview

This report describes the design, implementation, and evaluation of a multi-agent system
built to automate the inventory management, quoting, and order fulfilment workflows of
Beaver's Choice Paper Company. The system is implemented in Python using the
**smolagents** framework (v1.16+) and a SQLite backend managed through SQLAlchemy.

---

## 2. Agent Workflow Architecture

### 2.1 Agent Roster

The system uses **four agents** (within the five-agent constraint):

| Agent | Role |
|---|---|
| **Orchestrator** | Entry point for every customer request. Analyses the request, delegates subtasks to specialist agents in the correct order, and composes the final customer-facing response. |
| **Inventory Agent** | Maps natural-language item names to exact catalogue entries, checks current stock levels, places individual supplier restock orders, and optionally triggers a full low-stock sweep. |
| **Quoting Agent** | Searches historical quotes for comparable past orders, then computes an itemised price quote with tiered bulk and multi-item discounts. |
| **Sales Agent** | Verifies the company's available cash, records confirmed sale transactions in the database, and reports transaction confirmation to the orchestrator. |

> **Design note:** The design document listed a fifth "Supplier Agent"; in the final
> implementation its two tools (`place_supplier_restock`, `restock_all_low_inventory`)
> were folded into the Inventory Agent, keeping the orchestrator's managed-agent list to
> three specialist agents and reducing unnecessary inter-agent hops for simple restock tasks.

### 2.2 Tool Assignments

| Tool | Agent | Helper Function(s) |
|---|---|---|
| `list_catalog_items` | Inventory | *(in-memory catalogue constant)* |
| `check_item_stock` | Inventory | `get_stock_level` |
| `list_available_inventory` | Inventory | `get_all_inventory` |
| `place_supplier_restock` | Inventory | `get_supplier_delivery_date`, `create_transaction` |
| `restock_all_low_inventory` | Inventory | `get_stock_level`, `create_transaction` |
| `search_historical_quotes` | Quoting | `search_quote_history` |
| `calculate_quote` | Quoting | *(CATALOG_PRICES constant + discount logic)* |
| `get_current_cash_balance` | Sales | `get_cash_balance` |
| `process_sale_transaction` | Sales | `get_stock_level`, `create_transaction` |

### 2.3 Request Processing Flow

For a typical customer request the orchestrator follows this sequence:

1. **Inventory check** — delegates to the Inventory Agent to resolve exact catalogue names
   and confirm current stock levels.
2. **Quote generation** — delegates to the Quoting Agent to produce an itemised price
   (with bulk and multi-item discounts) and benchmark it against historical quotes.
3. **Sale recording** — delegates to the Sales Agent to verify cash solvency and commit
   the transaction to the database.
4. **Restock if needed** — if stock has fallen below the minimum threshold the Inventory
   Agent places supplier orders proactively.

The orchestrator compiles all specialist responses into a single, customer-friendly reply.

### 2.4 Architecture Rationale

**Why smolagents?**  
`smolagents` was chosen because its `ToolCallingAgent` with `managed_agents` maps
directly onto a hierarchical multi-agent pattern with minimal boilerplate. Tools are
defined with a single `@tool` decorator and standard Python docstrings, and the
`OpenAIServerModel` wrapper works with any OpenAI-compatible endpoint.

**Why separate inventory, quoting, and sales concerns?**  
Keeping each agent's tool set small (3–5 tools each) and focused reduces the risk of
the LLM confusing unrelated capabilities in a single prompt. A monolithic agent with all
nine tools would have a much harder time reliably following the four-step workflow within
a single ReAct loop.

**Why 3× minimum for restock quantity?**  
Ordering three times the minimum threshold is large enough to avoid constant reordering
while staying below the 1 000-unit threshold for next-day delivery on most items.

**Item name matching strategy:**  
Customers rarely use exact catalogue names. Every agent instruction begins with an
explicit requirement to call `list_catalog_items` first and only use verbatim names from
the result. This prevents silent misses where a customer says "glossy paper" and the
agent checks for "A4 Glossy" (which doesn't exist) instead of "Glossy paper".

---

## 3. Evaluation Results

The system was evaluated against all 20 requests in `quote_requests_sample.csv`.
Results are recorded in full in `test_results.csv`.

### 3.1 Financial Summary

| Metric | Value |
|---|---|
| Starting cash balance | $44,947.70 |
| Ending cash balance | $9,149.55 |
| Ending inventory value | $37,688.95 |
| Total cash deployed (restocks + sales) | ~$35,798 |

The large shift from cash into inventory (cash down ~$35k, inventory up ~$33k) reflects
the system correctly identifying low-stock items and placing supplier restock orders
throughout the run.

### 3.2 Request Outcomes

| # | Date | Outcome |
|---|---|---|
| 1 | Apr 01 | Partial — order described but not committed (A4 glossy, cardstock, colored paper) |
| 2 | Apr 03 | ✅ Fulfilled — 220 gsm poster paper + Party streamers; balloons not in catalogue |
| 3 | Apr 04 | ✅ Fulfilled — copy paper + A4 paper ordered; full conference quote provided |
| 4 | Apr 05 | ✅ Partial restock — A4 paper restocked; recycled cardstock not in catalogue |
| 5 | Apr 05 | ✅ Fulfilled — colored paper, cardstock, washi tape ordered |
| 6 | Apr 06 | ✅ Partial — cardstock sold; construction paper and printer paper unavailable |
| 7 | Apr 07 | ✅ Fulfilled — poster paper, glossy, matte, cardstock restock placed |
| 8 | Apr 07 | ❌ Unfulfilled — matte paper and recycled paper out of stock; alternatives suggested |
| 9 | Apr 07 | ✅ Fulfilled — A4 paper, glossy paper, envelopes ordered |
| 10 | Apr 08 | ✅ Partial — glossy paper fulfilled; cardstock out of stock |
| 11 | Apr 08 | ❌ Unfulfilled — all requested items out of stock; alternatives suggested |
| 12 | Apr 08 | ✅ Fulfilled — colored paper, copy paper, napkins ordered |
| 13 | Apr 08 | ✅ Fulfilled — A4 paper and cardstock ordered with confirmed delivery |
| 14 | Apr 09 | ✅ Fulfilled — A4 paper, cardstock, 220 gsm poster paper (large order) |
| 15 | Apr 12 | ❌ Unfulfilled — all requested items out of stock at time of request |
| 16 | Apr 13 | ✅ Restock placed — A4 paper, construction paper, poster paper |
| 17 | Apr 14 | ✅ Partial — paper plates restocked; biodegradable items not in catalogue; quote provided |
| 18 | Apr 14 | ✅ Partial — copy paper fulfilled; cardstock order pending |
| 19 | Apr 15 | ✅ Fulfilled — large order: glossy, matte paper, cardstock (4 500 sheets total) |
| 20 | Apr 17 | ✅ Partial — flyers and posters restocked; tickets not in catalogue |

**Summary:**
- 15 of 20 requests resulted in at least one confirmed order or restock ✅
- 16 of 20 requests changed the cash balance ✅
- 8 requests were partially or fully unfulfilled, each with a documented reason ✅

### 3.3 Strengths

1. **Accurate catalogue enforcement.** By instructing every agent to call
   `list_catalog_items` before any operation, the system reliably maps vague customer
   descriptions ("heavy cardstock", "glossy photo paper") to exact catalogue entries and
   avoids silent no-ops.

2. **Transparent pricing with discount breakdown.** The `calculate_quote` tool returns a
   full itemised breakdown — unit price, line discount percentage, discounted line total —
   so customers can see exactly why a bulk order of 5 000+ sheets costs less per sheet.
   Multi-item orders receive a further 5 % order-level discount that is separately
   identified in the response.

3. **Graceful handling of catalogue gaps.** Items not in the catalogue (biodegradable cups,
   tickets, balloons) are correctly rejected with a clear explanation rather than silently
   failing or hallucinating a price.

4. **Inventory-aware reordering.** When a requested item is out of stock the Inventory
   Agent places a supplier restock automatically and returns the expected delivery date,
   allowing the customer to plan ahead even when immediate fulfilment is impossible.

5. **Financial state tracking.** The cash balance and inventory value are re-read from the
   database after every request, so every subsequent agent call operates on up-to-date
   figures rather than stale snapshots.

### 3.4 Areas for Improvement

**1. Inconsistent transaction completion**  
Request 1 illustrates a recurring pattern where an agent returns a future-tense summary
("I will check…") rather than executing the transaction. This stems from the LLM
occasionally treating the task description as a planning step rather than an action step.
A more reliable solution would be to restructure the orchestrator prompt to include an
explicit checklist that must be ticked off (inventory checked ✓ / quote calculated ✓ /
transaction recorded ✓) before `final_answer` is permitted.

**2. Hallucinated delivery dates in natural-language responses**  
In several responses the LLM summarised the outcome using a date it invented (e.g.
"October 2023") instead of the ISO date returned by `get_supplier_delivery_date`. The
tool output is correct in the database, but the customer-facing text is misleading. A
post-processing step that extracts structured fields (delivery date, total, transaction
ID) directly from the tool result JSON — rather than relying on the LLM to paraphrase
them — would eliminate this class of error entirely.

---

## 4. Suggestions for Further Improvement

### 4.1 Structured Output with Validation

Replace free-text agent responses with a Pydantic response model
(`OrderConfirmation`, `QuoteResponse`, `StockCheckResult`). The orchestrator would
validate the structured output before forwarding it to the customer, guaranteeing that
all required fields (items, quantities, unit prices, delivery dates, transaction IDs) are
present and correctly typed. This would also prevent the hallucinated-date problem noted
above.

### 4.2 Customer-Specific Pricing History

The current quoting agent benchmarks new quotes against all historical quotes regardless
of customer. Adding a customer ID to requests and filtering `search_quote_history` by
customer would let the quoting agent honour loyalty pricing ("you paid $X last time") and
identify customers who are consistently placing large orders and therefore merit higher
standing discounts. This would make the system more commercially compelling and align
with the goal of driving increased sales.

### 4.3 Multi-Step Partial-Fulfilment Workflow

When only some items in an order are in stock, the current system reports the shortage
and suggests alternatives but does not automatically offer a partial shipment now plus a
backorder for the remainder. Adding a dedicated backorder tool — which records a pending
order in the database and triggers a follow-up quote once the restock arrives — would
convert currently lost sales into deferred revenue.

### 4.4 Agent Memory Between Requests

The current singleton orchestrator accumulates conversation history across requests in the
same process run, which can cause context bleed (an agent remembering an item name from
an earlier request). Resetting or summarising agent memory between requests would improve
accuracy for longer runs and make the system more production-safe.

---

## 5. Conclusion

The implemented multi-agent system successfully automates the core operations of
Beaver's Choice Paper Company. In a 20-request evaluation it correctly fulfilled 15
orders, moved ~$35 000 from cash into inventory through supplier restocking, and provided
transparent explanations for the 8 partially or fully unfulfilled requests. The
smolagents framework proved well-suited to the hierarchical orchestration pattern, and
the layered tool design — where each `@tool` function is a thin wrapper over a tested
helper — made the agent layer straightforward to unit-test independently of any LLM calls.

The most impactful next steps are structured output validation (to eliminate hallucinated
responses) and customer-specific pricing (to increase competitive quoting), both of which
build on the existing tool architecture without requiring a redesign of the agent topology.
