import pandas as pd
import numpy as np
import os
import json
import time
import dotenv
import ast
from sqlalchemy.sql import text
from datetime import datetime, timedelta
from typing import Dict, List, Union
from sqlalchemy import create_engine, Engine

# Create an SQLite database
db_engine = create_engine("sqlite:///munder_difflin.db")

# List containing the different kinds of papers 
paper_supplies = [
    # Paper Types (priced per sheet unless specified)
    {"item_name": "A4 paper",                         "category": "paper",        "unit_price": 0.05},
    {"item_name": "Letter-sized paper",              "category": "paper",        "unit_price": 0.06},
    {"item_name": "Cardstock",                        "category": "paper",        "unit_price": 0.15},
    {"item_name": "Colored paper",                    "category": "paper",        "unit_price": 0.10},
    {"item_name": "Glossy paper",                     "category": "paper",        "unit_price": 0.20},
    {"item_name": "Matte paper",                      "category": "paper",        "unit_price": 0.18},
    {"item_name": "Recycled paper",                   "category": "paper",        "unit_price": 0.08},
    {"item_name": "Eco-friendly paper",               "category": "paper",        "unit_price": 0.12},
    {"item_name": "Poster paper",                     "category": "paper",        "unit_price": 0.25},
    {"item_name": "Banner paper",                     "category": "paper",        "unit_price": 0.30},
    {"item_name": "Kraft paper",                      "category": "paper",        "unit_price": 0.10},
    {"item_name": "Construction paper",               "category": "paper",        "unit_price": 0.07},
    {"item_name": "Wrapping paper",                   "category": "paper",        "unit_price": 0.15},
    {"item_name": "Glitter paper",                    "category": "paper",        "unit_price": 0.22},
    {"item_name": "Decorative paper",                 "category": "paper",        "unit_price": 0.18},
    {"item_name": "Letterhead paper",                 "category": "paper",        "unit_price": 0.12},
    {"item_name": "Legal-size paper",                 "category": "paper",        "unit_price": 0.08},
    {"item_name": "Crepe paper",                      "category": "paper",        "unit_price": 0.05},
    {"item_name": "Photo paper",                      "category": "paper",        "unit_price": 0.25},
    {"item_name": "Uncoated paper",                   "category": "paper",        "unit_price": 0.06},
    {"item_name": "Butcher paper",                    "category": "paper",        "unit_price": 0.10},
    {"item_name": "Heavyweight paper",                "category": "paper",        "unit_price": 0.20},
    {"item_name": "Standard copy paper",              "category": "paper",        "unit_price": 0.04},
    {"item_name": "Bright-colored paper",             "category": "paper",        "unit_price": 0.12},
    {"item_name": "Patterned paper",                  "category": "paper",        "unit_price": 0.15},

    # Product Types (priced per unit)
    {"item_name": "Paper plates",                     "category": "product",      "unit_price": 0.10},  # per plate
    {"item_name": "Paper cups",                       "category": "product",      "unit_price": 0.08},  # per cup
    {"item_name": "Paper napkins",                    "category": "product",      "unit_price": 0.02},  # per napkin
    {"item_name": "Disposable cups",                  "category": "product",      "unit_price": 0.10},  # per cup
    {"item_name": "Table covers",                     "category": "product",      "unit_price": 1.50},  # per cover
    {"item_name": "Envelopes",                        "category": "product",      "unit_price": 0.05},  # per envelope
    {"item_name": "Sticky notes",                     "category": "product",      "unit_price": 0.03},  # per sheet
    {"item_name": "Notepads",                         "category": "product",      "unit_price": 2.00},  # per pad
    {"item_name": "Invitation cards",                 "category": "product",      "unit_price": 0.50},  # per card
    {"item_name": "Flyers",                           "category": "product",      "unit_price": 0.15},  # per flyer
    {"item_name": "Party streamers",                  "category": "product",      "unit_price": 0.05},  # per roll
    {"item_name": "Decorative adhesive tape (washi tape)", "category": "product", "unit_price": 0.20},  # per roll
    {"item_name": "Paper party bags",                 "category": "product",      "unit_price": 0.25},  # per bag
    {"item_name": "Name tags with lanyards",          "category": "product",      "unit_price": 0.75},  # per tag
    {"item_name": "Presentation folders",             "category": "product",      "unit_price": 0.50},  # per folder

    # Large-format items (priced per unit)
    {"item_name": "Large poster paper (24x36 inches)", "category": "large_format", "unit_price": 1.00},
    {"item_name": "Rolls of banner paper (36-inch width)", "category": "large_format", "unit_price": 2.50},

    # Specialty papers
    {"item_name": "100 lb cover stock",               "category": "specialty",    "unit_price": 0.50},
    {"item_name": "80 lb text paper",                 "category": "specialty",    "unit_price": 0.40},
    {"item_name": "250 gsm cardstock",                "category": "specialty",    "unit_price": 0.30},
    {"item_name": "220 gsm poster paper",             "category": "specialty",    "unit_price": 0.35},
]

# Given below are some utility functions you can use to implement your multi-agent system

def generate_sample_inventory(paper_supplies: list, coverage: float = 0.4, seed: int = 137) -> pd.DataFrame:
    """
    Generate inventory for exactly a specified percentage of items from the full paper supply list.

    This function randomly selects exactly `coverage` × N items from the `paper_supplies` list,
    and assigns each selected item:
    - a random stock quantity between 200 and 800,
    - a minimum stock level between 50 and 150.

    The random seed ensures reproducibility of selection and stock levels.

    Args:
        paper_supplies (list): A list of dictionaries, each representing a paper item with
                               keys 'item_name', 'category', and 'unit_price'.
        coverage (float, optional): Fraction of items to include in the inventory (default is 0.4, or 40%).
        seed (int, optional): Random seed for reproducibility (default is 137).

    Returns:
        pd.DataFrame: A DataFrame with the selected items and assigned inventory values, including:
                      - item_name
                      - category
                      - unit_price
                      - current_stock
                      - min_stock_level
    """
    # Ensure reproducible random output
    np.random.seed(seed)

    # Calculate number of items to include based on coverage
    num_items = int(len(paper_supplies) * coverage)

    # Randomly select item indices without replacement
    selected_indices = np.random.choice(
        range(len(paper_supplies)),
        size=num_items,
        replace=False
    )

    # Extract selected items from paper_supplies list
    selected_items = [paper_supplies[i] for i in selected_indices]

    # Construct inventory records
    inventory = []
    for item in selected_items:
        inventory.append({
            "item_name": item["item_name"],
            "category": item["category"],
            "unit_price": item["unit_price"],
            "current_stock": np.random.randint(200, 800),  # Realistic stock range
            "min_stock_level": np.random.randint(50, 150)  # Reasonable threshold for reordering
        })

    # Return inventory as a pandas DataFrame
    return pd.DataFrame(inventory)

def init_database(db_engine: Engine, seed: int = 137) -> Engine:    
    """
    Set up the Munder Difflin database with all required tables and initial records.

    This function performs the following tasks:
    - Creates the 'transactions' table for logging stock orders and sales
    - Loads customer inquiries from 'quote_requests.csv' into a 'quote_requests' table
    - Loads previous quotes from 'quotes.csv' into a 'quotes' table, extracting useful metadata
    - Generates a random subset of paper inventory using `generate_sample_inventory`
    - Inserts initial financial records including available cash and starting stock levels

    Args:
        db_engine (Engine): A SQLAlchemy engine connected to the SQLite database.
        seed (int, optional): A random seed used to control reproducibility of inventory stock levels.
                              Default is 137.

    Returns:
        Engine: The same SQLAlchemy engine, after initializing all necessary tables and records.

    Raises:
        Exception: If an error occurs during setup, the exception is printed and raised.
    """
    try:
        # ----------------------------
        # 1. Create an empty 'transactions' table schema
        # ----------------------------
        transactions_schema = pd.DataFrame({
            "id": [],
            "item_name": [],
            "transaction_type": [],  # 'stock_orders' or 'sales'
            "units": [],             # Quantity involved
            "price": [],             # Total price for the transaction
            "transaction_date": [],  # ISO-formatted date
        })
        transactions_schema.to_sql("transactions", db_engine, if_exists="replace", index=False)

        # Set a consistent starting date
        initial_date = datetime(2025, 1, 1).isoformat()

        # ----------------------------
        # 2. Load and initialize 'quote_requests' table
        # ----------------------------
        quote_requests_df = pd.read_csv("quote_requests.csv")
        quote_requests_df["id"] = range(1, len(quote_requests_df) + 1)
        quote_requests_df.to_sql("quote_requests", db_engine, if_exists="replace", index=False)

        # ----------------------------
        # 3. Load and transform 'quotes' table
        # ----------------------------
        quotes_df = pd.read_csv("quotes.csv")
        quotes_df["request_id"] = range(1, len(quotes_df) + 1)
        quotes_df["order_date"] = initial_date

        # Unpack metadata fields (job_type, order_size, event_type) if present
        if "request_metadata" in quotes_df.columns:
            quotes_df["request_metadata"] = quotes_df["request_metadata"].apply(
                lambda x: ast.literal_eval(x) if isinstance(x, str) else x
            )
            quotes_df["job_type"] = quotes_df["request_metadata"].apply(lambda x: x.get("job_type", ""))
            quotes_df["order_size"] = quotes_df["request_metadata"].apply(lambda x: x.get("order_size", ""))
            quotes_df["event_type"] = quotes_df["request_metadata"].apply(lambda x: x.get("event_type", ""))

        # Retain only relevant columns
        quotes_df = quotes_df[[
            "request_id",
            "total_amount",
            "quote_explanation",
            "order_date",
            "job_type",
            "order_size",
            "event_type"
        ]]
        quotes_df.to_sql("quotes", db_engine, if_exists="replace", index=False)

        # ----------------------------
        # 4. Generate inventory and seed stock
        # ----------------------------
        inventory_df = generate_sample_inventory(paper_supplies, seed=seed)

        # Seed initial transactions
        initial_transactions = []

        # Add a starting cash balance via a dummy sales transaction
        initial_transactions.append({
            "item_name": None,
            "transaction_type": "sales",
            "units": None,
            "price": 50000.0,
            "transaction_date": initial_date,
        })

        # Add one stock order transaction per inventory item
        for _, item in inventory_df.iterrows():
            initial_transactions.append({
                "item_name": item["item_name"],
                "transaction_type": "stock_orders",
                "units": item["current_stock"],
                "price": item["current_stock"] * item["unit_price"],
                "transaction_date": initial_date,
            })

        # Commit transactions to database
        pd.DataFrame(initial_transactions).to_sql("transactions", db_engine, if_exists="append", index=False)

        # Save the inventory reference table
        inventory_df.to_sql("inventory", db_engine, if_exists="replace", index=False)

        return db_engine

    except Exception as e:
        print(f"Error initializing database: {e}")
        raise

def create_transaction(
    item_name: str,
    transaction_type: str,
    quantity: int,
    price: float,
    date: Union[str, datetime],
) -> int:
    """
    This function records a transaction of type 'stock_orders' or 'sales' with a specified
    item name, quantity, total price, and transaction date into the 'transactions' table of the database.

    Args:
        item_name (str): The name of the item involved in the transaction.
        transaction_type (str): Either 'stock_orders' or 'sales'.
        quantity (int): Number of units involved in the transaction.
        price (float): Total price of the transaction.
        date (str or datetime): Date of the transaction in ISO 8601 format.

    Returns:
        int: The ID of the newly inserted transaction.

    Raises:
        ValueError: If `transaction_type` is not 'stock_orders' or 'sales'.
        Exception: For other database or execution errors.
    """
    try:
        # Convert datetime to ISO string if necessary
        date_str = date.isoformat() if isinstance(date, datetime) else date

        # Validate transaction type
        if transaction_type not in {"stock_orders", "sales"}:
            raise ValueError("Transaction type must be 'stock_orders' or 'sales'")

        # Prepare transaction record as a single-row DataFrame
        transaction = pd.DataFrame([{
            "item_name": item_name,
            "transaction_type": transaction_type,
            "units": quantity,
            "price": price,
            "transaction_date": date_str,
        }])

        # Insert the record into the database
        transaction.to_sql("transactions", db_engine, if_exists="append", index=False)

        # Fetch and return the ID of the inserted row
        result = pd.read_sql("SELECT last_insert_rowid() as id", db_engine)
        return int(result.iloc[0]["id"])

    except Exception as e:
        print(f"Error creating transaction: {e}")
        raise

def get_all_inventory(as_of_date: str) -> Dict[str, int]:
    """
    Retrieve a snapshot of available inventory as of a specific date.

    This function calculates the net quantity of each item by summing 
    all stock orders and subtracting all sales up to and including the given date.

    Only items with positive stock are included in the result.

    Args:
        as_of_date (str): ISO-formatted date string (YYYY-MM-DD) representing the inventory cutoff.

    Returns:
        Dict[str, int]: A dictionary mapping item names to their current stock levels.
    """
    # SQL query to compute stock levels per item as of the given date
    query = """
        SELECT
            item_name,
            SUM(CASE
                WHEN transaction_type = 'stock_orders' THEN units
                WHEN transaction_type = 'sales' THEN -units
                ELSE 0
            END) as stock
        FROM transactions
        WHERE item_name IS NOT NULL
        AND transaction_date <= :as_of_date
        GROUP BY item_name
        HAVING stock > 0
    """

    # Execute the query with the date parameter
    result = pd.read_sql(query, db_engine, params={"as_of_date": as_of_date})

    # Convert the result into a dictionary {item_name: stock}
    return dict(zip(result["item_name"], result["stock"]))

def get_stock_level(item_name: str, as_of_date: Union[str, datetime]) -> pd.DataFrame:
    """
    Retrieve the stock level of a specific item as of a given date.

    This function calculates the net stock by summing all 'stock_orders' and 
    subtracting all 'sales' transactions for the specified item up to the given date.

    Args:
        item_name (str): The name of the item to look up.
        as_of_date (str or datetime): The cutoff date (inclusive) for calculating stock.

    Returns:
        pd.DataFrame: A single-row DataFrame with columns 'item_name' and 'current_stock'.
    """
    # Convert date to ISO string format if it's a datetime object
    if isinstance(as_of_date, datetime):
        as_of_date = as_of_date.isoformat()

    # SQL query to compute net stock level for the item
    stock_query = """
        SELECT
            item_name,
            COALESCE(SUM(CASE
                WHEN transaction_type = 'stock_orders' THEN units
                WHEN transaction_type = 'sales' THEN -units
                ELSE 0
            END), 0) AS current_stock
        FROM transactions
        WHERE item_name = :item_name
        AND transaction_date <= :as_of_date
    """

    # Execute query and return result as a DataFrame
    return pd.read_sql(
        stock_query,
        db_engine,
        params={"item_name": item_name, "as_of_date": as_of_date},
    )

def get_supplier_delivery_date(input_date_str: str, quantity: int) -> str:
    """
    Estimate the supplier delivery date based on the requested order quantity and a starting date.

    Delivery lead time increases with order size:
        - ≤10 units: same day
        - 11–100 units: 1 day
        - 101–1000 units: 4 days
        - >1000 units: 7 days

    Args:
        input_date_str (str): The starting date in ISO format (YYYY-MM-DD).
        quantity (int): The number of units in the order.

    Returns:
        str: Estimated delivery date in ISO format (YYYY-MM-DD).
    """
    # Debug log (comment out in production if needed)
    print(f"FUNC (get_supplier_delivery_date): Calculating for qty {quantity} from date string '{input_date_str}'")

    # Attempt to parse the input date
    try:
        input_date_dt = datetime.fromisoformat(input_date_str.split("T")[0])
    except (ValueError, TypeError):
        # Fallback to current date on format error
        print(f"WARN (get_supplier_delivery_date): Invalid date format '{input_date_str}', using today as base.")
        input_date_dt = datetime.now()

    # Determine delivery delay based on quantity
    if quantity <= 10:
        days = 0
    elif quantity <= 100:
        days = 1
    elif quantity <= 1000:
        days = 4
    else:
        days = 7

    # Add delivery days to the starting date
    delivery_date_dt = input_date_dt + timedelta(days=days)

    # Return formatted delivery date
    return delivery_date_dt.strftime("%Y-%m-%d")

def get_cash_balance(as_of_date: Union[str, datetime]) -> float:
    """
    Calculate the current cash balance as of a specified date.

    The balance is computed by subtracting total stock purchase costs ('stock_orders')
    from total revenue ('sales') recorded in the transactions table up to the given date.

    Args:
        as_of_date (str or datetime): The cutoff date (inclusive) in ISO format or as a datetime object.

    Returns:
        float: Net cash balance as of the given date. Returns 0.0 if no transactions exist or an error occurs.
    """
    try:
        # Convert date to ISO format if it's a datetime object
        if isinstance(as_of_date, datetime):
            as_of_date = as_of_date.isoformat()

        # Query all transactions on or before the specified date
        transactions = pd.read_sql(
            "SELECT * FROM transactions WHERE transaction_date <= :as_of_date",
            db_engine,
            params={"as_of_date": as_of_date},
        )

        # Compute the difference between sales and stock purchases
        if not transactions.empty:
            total_sales = transactions.loc[transactions["transaction_type"] == "sales", "price"].sum()
            total_purchases = transactions.loc[transactions["transaction_type"] == "stock_orders", "price"].sum()
            return float(total_sales - total_purchases)

        return 0.0

    except Exception as e:
        print(f"Error getting cash balance: {e}")
        return 0.0


def generate_financial_report(as_of_date: Union[str, datetime]) -> Dict:
    """
    Generate a complete financial report for the company as of a specific date.

    This includes:
    - Cash balance
    - Inventory valuation
    - Combined asset total
    - Itemized inventory breakdown
    - Top 5 best-selling products

    Args:
        as_of_date (str or datetime): The date (inclusive) for which to generate the report.

    Returns:
        Dict: A dictionary containing the financial report fields:
            - 'as_of_date': The date of the report
            - 'cash_balance': Total cash available
            - 'inventory_value': Total value of inventory
            - 'total_assets': Combined cash and inventory value
            - 'inventory_summary': List of items with stock and valuation details
            - 'top_selling_products': List of top 5 products by revenue
    """
    # Normalize date input
    if isinstance(as_of_date, datetime):
        as_of_date = as_of_date.isoformat()

    # Get current cash balance
    cash = get_cash_balance(as_of_date)

    # Get current inventory snapshot
    inventory_df = pd.read_sql("SELECT * FROM inventory", db_engine)
    inventory_value = 0.0
    inventory_summary = []

    # Compute total inventory value and summary by item
    for _, item in inventory_df.iterrows():
        stock_info = get_stock_level(item["item_name"], as_of_date)
        stock = stock_info["current_stock"].iloc[0]
        item_value = stock * item["unit_price"]
        inventory_value += item_value

        inventory_summary.append({
            "item_name": item["item_name"],
            "stock": stock,
            "unit_price": item["unit_price"],
            "value": item_value,
        })

    # Identify top-selling products by revenue
    top_sales_query = """
        SELECT item_name, SUM(units) as total_units, SUM(price) as total_revenue
        FROM transactions
        WHERE transaction_type = 'sales' AND transaction_date <= :date
        GROUP BY item_name
        ORDER BY total_revenue DESC
        LIMIT 5
    """
    top_sales = pd.read_sql(top_sales_query, db_engine, params={"date": as_of_date})
    top_selling_products = top_sales.to_dict(orient="records")

    return {
        "as_of_date": as_of_date,
        "cash_balance": cash,
        "inventory_value": inventory_value,
        "total_assets": cash + inventory_value,
        "inventory_summary": inventory_summary,
        "top_selling_products": top_selling_products,
    }


def search_quote_history(search_terms: List[str], limit: int = 5) -> List[Dict]:
    """
    Retrieve a list of historical quotes that match any of the provided search terms.

    The function searches both the original customer request (from `quote_requests`) and
    the explanation for the quote (from `quotes`) for each keyword. Results are sorted by
    most recent order date and limited by the `limit` parameter.

    Args:
        search_terms (List[str]): List of terms to match against customer requests and explanations.
        limit (int, optional): Maximum number of quote records to return. Default is 5.

    Returns:
        List[Dict]: A list of matching quotes, each represented as a dictionary with fields:
            - original_request
            - total_amount
            - quote_explanation
            - job_type
            - order_size
            - event_type
            - order_date
    """
    conditions = []
    params = {}

    # Build SQL WHERE clause using LIKE filters for each search term
    for i, term in enumerate(search_terms):
        param_name = f"term_{i}"
        conditions.append(
            f"(LOWER(qr.response) LIKE :{param_name} OR "
            f"LOWER(q.quote_explanation) LIKE :{param_name})"
        )
        params[param_name] = f"%{term.lower()}%"

    # Combine conditions; fallback to always-true if no terms provided
    where_clause = " AND ".join(conditions) if conditions else "1=1"

    # Final SQL query to join quotes with quote_requests
    query = f"""
        SELECT
            qr.response AS original_request,
            q.total_amount,
            q.quote_explanation,
            q.job_type,
            q.order_size,
            q.event_type,
            q.order_date
        FROM quotes q
        JOIN quote_requests qr ON q.request_id = qr.id
        WHERE {where_clause}
        ORDER BY q.order_date DESC
        LIMIT {limit}
    """

    # Execute parameterized query
    with db_engine.connect() as conn:
        result = conn.execute(text(query), params)
        return [dict(row._mapping) for row in result]

########################
########################
########################
# YOUR MULTI AGENT STARTS HERE
########################
########################
########################

from smolagents import OpenAIServerModel, ToolCallingAgent, tool  # noqa: E402

# Catalogue price lookup (item_name → unit_price)
CATALOG_PRICES: Dict[str, float] = {
    item["item_name"]: item["unit_price"] for item in paper_supplies
}

# When auto-restocking, order this multiple of the item's minimum stock level
_DEFAULT_RESTOCK_MULTIPLIER = 3


def _bulk_discount_rate(qty: int) -> int:
    """Return the bulk discount percentage for the given quantity."""
    if qty >= 5000:
        return 15
    if qty >= 1000:
        return 10
    if qty > 200:
        return 5
    return 0


# ─────────────────────────────────────────────────────────────
# INVENTORY AGENT TOOLS
# ─────────────────────────────────────────────────────────────

@tool
def list_catalog_items() -> str:
    """
    List every paper product in the Beaver's Choice Paper Company catalog with
    its category and unit price.

    Returns:
        A formatted multi-line string containing every catalog item and its
        price per unit, grouped by category.
    """
    lines = ["Beaver's Choice Paper Company — Full Catalog:"]
    for item in paper_supplies:
        lines.append(
            f"  {item['item_name']} ({item['category']}): ${item['unit_price']:.4f}/unit"
        )
    return "\n".join(lines)


@tool
def check_item_stock(item_name: str, date: str) -> str:
    """
    Report the current stock level for a single catalog item.

    Args:
        item_name: The exact name of the catalog item to check (case-sensitive).
        date: The as-of date in YYYY-MM-DD format.

    Returns:
        A human-readable string reporting the item's available units on the
        given date, or an out-of-stock message if none are available.
    """
    stock_df = get_stock_level(item_name, date)
    stock = int(stock_df["current_stock"].iloc[0])
    if stock <= 0:
        return f"{item_name}: Out of stock (0 units available as of {date})"
    return f"{item_name}: {stock} units in stock as of {date}"


@tool
def list_available_inventory(date: str) -> str:
    """
    List every item currently in stock with its quantity and unit price.

    Args:
        date: The as-of date in YYYY-MM-DD format.

    Returns:
        A formatted string listing each in-stock item, its quantity, and
        catalog price, or a message indicating the warehouse is empty.
    """
    inventory = get_all_inventory(date)
    if not inventory:
        return f"No items currently in stock as of {date}."
    lines = [f"Available inventory as of {date}:"]
    for item_name, stock in sorted(inventory.items()):
        price = CATALOG_PRICES.get(item_name, 0.0)
        lines.append(f"  {item_name}: {stock} units @ ${price:.4f}/unit")
    return "\n".join(lines)


@tool
def restock_all_low_inventory(date: str) -> str:
    """
    Identify every item whose stock has fallen below its minimum level and
    automatically place supplier restock orders for each of them.

    Args:
        date: The as-of date in YYYY-MM-DD format used both to check current
              stock levels and to record the restock transactions.

    Returns:
        A JSON string with a top-level "restocked" key whose value is a list
        of dicts (one per restocked item) containing item_name, quantity,
        cost, and delivery_date.  Returns an empty list when all stock levels
        are adequate.
    """
    inventory_df = pd.read_sql("SELECT * FROM inventory", db_engine)
    restocked = []
    for _, item in inventory_df.iterrows():
        item_name = item["item_name"]
        min_stock = int(item["min_stock_level"])
        current = int(get_stock_level(item_name, date)["current_stock"].iloc[0])
        if current < min_stock:
            restock_qty = min_stock * _DEFAULT_RESTOCK_MULTIPLIER
            unit_price = CATALOG_PRICES.get(item_name, float(item["unit_price"]))
            cost = round(restock_qty * unit_price, 2)
            create_transaction(item_name, "stock_orders", restock_qty, cost, date)
            delivery_date = get_supplier_delivery_date(date, restock_qty)
            restocked.append({
                "item_name": item_name,
                "quantity": restock_qty,
                "cost": cost,
                "delivery_date": delivery_date,
            })
    return json.dumps({"restocked": restocked})


# ─────────────────────────────────────────────────────────────
# QUOTING AGENT TOOLS
# ─────────────────────────────────────────────────────────────

@tool
def calculate_quote(items_json: str, date: str) -> str:
    """
    Calculate a price quote for one or more catalog items, applying bulk and
    multi-item discounts automatically.

    Bulk discount tiers (applied per line item):
      - 5000 or more units  →  15 % off the line
      - 1000 or more units  →  10 % off the line
      - More than 200 units →   5 % off the line
      - 200 units or fewer  →   no discount

    Orders with more than one distinct item also receive an additional 5 %
    discount applied to the combined subtotal.

    Args:
        items_json: A JSON-encoded list of objects, each with the keys
                    "item_name" (str) and "quantity" (int).
                    Example: '[{"item_name": "A4 paper", "quantity": 500}]'
        date: The quote date in YYYY-MM-DD format (used for display context).

    Returns:
        A JSON string containing the full quote breakdown: per-item discounts,
        subtotal, multi_item_discount_pct, total, and currency.  Returns a
        JSON object with an "error" key if any item is not in the catalog.
    """
    try:
        items_list = json.loads(items_json)
    except (json.JSONDecodeError, TypeError) as exc:
        return json.dumps({"error": f"Invalid items_json: {exc}"})

    line_items = []
    for item in items_list:
        item_name = item.get("item_name", "")
        if item_name not in CATALOG_PRICES:
            return json.dumps({"error": f"Item '{item_name}' not found in catalog"})
        qty = int(item.get("quantity", 0))
        unit_price = CATALOG_PRICES[item_name]
        discount_pct = _bulk_discount_rate(qty)
        line_total = round(qty * unit_price * (1 - discount_pct / 100), 4)
        line_items.append({
            "item_name": item_name,
            "quantity": qty,
            "unit_price": unit_price,
            "bulk_discount_pct": discount_pct,
            "line_total": line_total,
        })

    subtotal = round(sum(i["line_total"] for i in line_items), 4)
    multi_item_pct = 5 if len(line_items) > 1 else 0
    total = round(subtotal * (1 - multi_item_pct / 100), 4)

    return json.dumps({
        "items": line_items,
        "subtotal": subtotal,
        "multi_item_discount_pct": multi_item_pct,
        "total": total,
        "currency": "USD",
    })


@tool
def search_historical_quotes(search_terms_json: str) -> str:
    """
    Search the historical quote database for records matching one or more keywords.

    Args:
        search_terms_json: A JSON-encoded list of search terms, for example
                           '["wedding", "500 guests"]'.  A plain string is
                           also accepted and treated as a single term.

    Returns:
        A formatted summary of the matching historical quotes, or a message
        stating that no matches were found.
    """
    try:
        terms = json.loads(search_terms_json)
        if not isinstance(terms, list):
            terms = [str(terms)]
    except (json.JSONDecodeError, TypeError):
        terms = [search_terms_json]

    results = search_quote_history(terms, limit=5)
    if not results:
        return "No matching historical quotes found."

    lines = [f"Found {len(results)} historical quote(s):"]
    for i, q in enumerate(results, 1):
        lines.append(
            f"\n[{i}] Request: {q.get('original_request', 'N/A')}\n"
            f"    Amount: ${q.get('total_amount', 0):.2f} | "
            f"Job: {q.get('job_type', 'N/A')} | "
            f"Event: {q.get('event_type', 'N/A')}\n"
            f"    Explanation: {q.get('quote_explanation', 'N/A')}"
        )
    return "\n".join(lines)


# ─────────────────────────────────────────────────────────────
# SALES AGENT TOOLS
# ─────────────────────────────────────────────────────────────

@tool
def get_current_cash_balance(date: str) -> str:
    """
    Retrieve the company's current cash balance as of a given date.

    Args:
        date: The as-of date in YYYY-MM-DD format.

    Returns:
        A human-readable string reporting the available cash balance in USD.
    """
    balance = get_cash_balance(date)
    return f"Cash balance as of {date}: ${balance:,.2f}"


@tool
def process_sale_transaction(item_name: str, quantity: int, unit_price: float, date: str) -> str:
    """
    Finalise a confirmed sale by recording it in the database, reducing stock,
    and adding the proceeds to the company's cash balance.

    The transaction is rejected if there is insufficient stock on hand.

    Args:
        item_name: The exact catalog name of the item being sold.
        quantity: Number of units to sell (positive integer).
        unit_price: The agreed sale price per unit in USD.
        date: The transaction date in YYYY-MM-DD format.

    Returns:
        A JSON string.  On success: {"success": true, "transaction_id": ...,
        "item_name": ..., "quantity": ..., "unit_price": ..., "total": ...,
        "date": ...}.  On failure: {"success": false, "error": "..."}.
    """
    stock_df = get_stock_level(item_name, date)
    current_stock = int(stock_df["current_stock"].iloc[0])
    if current_stock < quantity:
        return json.dumps({
            "success": False,
            "error": (
                f"Insufficient stock for '{item_name}': "
                f"{current_stock} available, {quantity} requested"
            ),
        })

    total = round(quantity * unit_price, 2)
    try:
        tx_id = create_transaction(item_name, "sales", quantity, total, date)
        return json.dumps({
            "success": True,
            "transaction_id": tx_id,
            "item_name": item_name,
            "quantity": quantity,
            "unit_price": unit_price,
            "total": total,
            "date": date,
        })
    except Exception as exc:
        return json.dumps({"success": False, "error": str(exc)})


@tool
def place_supplier_restock(item_name: str, quantity: int, date: str) -> str:
    """
    Place a supplier restock order for a single catalog item, record the
    purchase cost, and return the expected delivery date.

    Args:
        item_name: The exact catalog name of the item to reorder.
        quantity: Number of units to order from the supplier.
        date: The order date in YYYY-MM-DD format.

    Returns:
        A JSON string.  On success: {"success": true, "item_name": ...,
        "quantity": ..., "cost": ..., "delivery_date": ..., "date": ...}.
        On failure: {"success": false, "error": "..."}.
    """
    if item_name not in CATALOG_PRICES:
        return json.dumps({
            "success": False,
            "error": f"Item '{item_name}' not found in catalog",
        })

    unit_price = CATALOG_PRICES[item_name]
    cost = round(quantity * unit_price, 2)
    delivery_date = get_supplier_delivery_date(date, quantity)

    try:
        create_transaction(item_name, "stock_orders", quantity, cost, date)
        return json.dumps({
            "success": True,
            "item_name": item_name,
            "quantity": quantity,
            "cost": cost,
            "delivery_date": delivery_date,
            "date": date,
        })
    except Exception as exc:
        return json.dumps({"success": False, "error": str(exc)})


# ─────────────────────────────────────────────────────────────
# AGENT ASSEMBLY (lazy singleton)
# ─────────────────────────────────────────────────────────────

_orchestrator_instance: "ToolCallingAgent | None" = None


def _build_orchestrator() -> ToolCallingAgent:
    """
    Construct the three specialist agents and the orchestrator that manages them.

    Called lazily so that LLM credentials are only needed at runtime, not at
    import time (which would break unit tests).
    """
    dotenv.load_dotenv()
    api_key = os.getenv("UDACITY_OPENAI_API_KEY") or os.getenv("OPENAI_API_KEY")
    api_base = os.getenv("OPENAI_API_BASE", "https://openai.vocareum.com/v1")
    model_id = os.getenv("OPENAI_MODEL", "gpt-4o-mini")

    model = OpenAIServerModel(
        model_id=model_id,
        api_base=api_base,
        api_key=api_key,
    )

    _catalog_hint = (
        "IMPORTANT: Always call list_catalog_items first to get the exact catalog "
        "item names. Only use item names that appear verbatim in the catalog response "
        "- never guess, shorten, or paraphrase them. "
        "CRITICAL: Complete every requested action NOW by calling the appropriate tools. "
        "Never say 'I will do X' or 'I am going to do X' - actually call the tool and do it. "
        "When reporting delivery dates, only use the exact date string returned by a tool call "
        "- never invent, estimate, or paraphrase a date. "
        "Always end your task by calling final_answer with a concise summary of what was done "
        "and the exact tool-returned values (quantities, prices, delivery dates)."
    )

    _inventory_hint = _catalog_hint + (
        " Do NOT call restock_all_low_inventory unless the customer explicitly asks "
        "for a full inventory restock of all items. For individual items use "
        "place_supplier_restock instead. Never restock proactively without being asked."
    )

    inventory_agent = ToolCallingAgent(
        tools=[
            list_catalog_items,
            check_item_stock,
            list_available_inventory,
            place_supplier_restock,
            restock_all_low_inventory,
        ],
        model=model,
        name="inventory_agent",
        description=(
            "Specialist for inventory operations. "
            "Use to check stock levels, list available inventory, look up catalog "
            "prices, place individual supplier restock orders, or auto-restock all "
            "items that have fallen below their minimum levels."
        ),
        max_steps=15,
        instructions=_inventory_hint,
    )

    quoting_agent = ToolCallingAgent(
        tools=[
            calculate_quote,
            search_historical_quotes,
            list_catalog_items,
            check_item_stock,
        ],
        model=model,
        name="quoting_agent",
        description=(
            "Specialist for generating price quotes. "
            "Use to calculate accurate quotes with bulk and multi-item discounts, "
            "search historical quote records for similar past orders, or look up "
            "catalog pricing."
        ),
        max_steps=10,
        instructions=_catalog_hint,
    )

    sales_agent = ToolCallingAgent(
        tools=[
            process_sale_transaction,
            get_current_cash_balance,
            check_item_stock,
        ],
        model=model,
        name="sales_agent",
        description=(
            "Specialist for finalising sales transactions. "
            "Use to process a confirmed sale (updates inventory and records revenue), "
            "verify available cash on hand, or confirm stock before committing."
        ),
        max_steps=10,
        instructions=_catalog_hint,
    )

    orchestrator = ToolCallingAgent(
        tools=[],
        model=model,
        managed_agents=[inventory_agent, quoting_agent, sales_agent],
        name="orchestrator",
        description=(
            "Top-level orchestrator for the Beaver's Choice Paper Company system. "
            "Routes customer inquiries to the appropriate specialist agent."
        ),
        max_steps=20,
        instructions=(
            "You are the orchestrator for Beaver's Choice Paper Company. "
            "You must COMPLETE every customer request, not describe it. "
            "Delegate each part of the request to the correct specialist agent and "
            "wait for its confirmed result before moving on. "
            "Always instruct each specialist to: (1) call list_catalog_items first, "
            "(2) use only exact catalog names, (3) actually execute all requested "
            "transactions, (4) report only dates and amounts returned by tool calls. "
            "Do not return a final answer until all actions (inventory checks, quotes, "
            "and sales) have been completed and confirmed by the specialist agents. "
            "Always end with a final_answer that summarises confirmed outcomes."
        ),
    )
    return orchestrator


def _get_orchestrator() -> ToolCallingAgent:
    """Return the singleton orchestrator, building it on first call."""
    global _orchestrator_instance
    if _orchestrator_instance is None:
        _orchestrator_instance = _build_orchestrator()
    return _orchestrator_instance


def handle_customer_request(request: str) -> str:
    """
    Process a customer inquiry end-to-end through the multi-agent system.

    The orchestrator receives the request and delegates to the appropriate
    specialist agent (inventory, quoting, or sales) as needed.

    Args:
        request: Natural-language customer inquiry, typically including a
                 "Date of request: YYYY-MM-DD" suffix added by the test harness.

    Returns:
        The agent's plain-text response string.
    """
    agent = _get_orchestrator()
    max_retries = 3
    for attempt in range(max_retries):
        try:
            result = agent.run(request)
            return str(result)
        except Exception as exc:
            error_str = str(exc)
            is_network = any(k in error_str for k in (
                "httpcore", "httpx", "RemoteProtocolError", "ConnectionError",
                "ReadTimeout", "ConnectTimeout", "Connection", "EOF",
            ))
            if is_network and attempt < max_retries - 1:
                wait = 10 * (attempt + 1)
                print(f"  [Retry {attempt+1}/{max_retries-1}] Network error, waiting {wait}s: {exc}")
                time.sleep(wait)
            else:
                return f"Error processing request: {exc}"
    return "Error: all retries exhausted"

def run_test_scenarios():
    """
    End-to-end test harness for the multi-agent system.

    Workflow:
    1. Calls init_database() to create a fresh SQLite database with inventory,
       historical quotes, and an opening cash balance of $50,000.
    2. Loads quote_requests_sample.csv, parses request dates, and sorts rows
       chronologically so requests are processed in order.
    3. Snapshots the initial financial position via generate_financial_report().
    4. Iterates over every sample request:
       - Prints context (requester role, event, date, current cash/inventory).
       - Appends the request date to the request text so agents have full context.
       - Passes the combined text to the multi-agent system (to be wired in).
       - Re-reads the financial report after the agent call to reflect any sales
         or restock transactions the agents recorded in the database.
       - Appends a result row (request_id, date, cash, inventory, response).
    5. Prints a final financial report showing end-of-run cash and inventory value.
    6. Writes all result rows to test_results.csv.

    Returns:
        list[dict]: One dict per processed request containing request_id,
                    request_date, cash_balance, inventory_value, and response.
    """
    print("Initializing Database...")
    init_database(db_engine)
    try:
        quote_requests_sample = pd.read_csv("quote_requests_sample.csv")
        quote_requests_sample["request_date"] = pd.to_datetime(
            quote_requests_sample["request_date"], format="%m/%d/%y", errors="coerce"
        )
        quote_requests_sample.dropna(subset=["request_date"], inplace=True)
        quote_requests_sample = quote_requests_sample.sort_values("request_date")
    except Exception as e:
        print(f"FATAL: Error loading test data: {e}")
        return

    # Get initial state
    initial_date = quote_requests_sample["request_date"].min().strftime("%Y-%m-%d")
    report = generate_financial_report(initial_date)
    current_cash = report["cash_balance"]
    current_inventory = report["inventory_value"]

    ############
    ############
    ############
    # INITIALIZE YOUR MULTI AGENT SYSTEM HERE
    ############
    ############
    ############

    results = []
    for idx, row in quote_requests_sample.iterrows():
        request_date = row["request_date"].strftime("%Y-%m-%d")

        print(f"\n=== Request {idx+1} ===")
        print(f"Context: {row['job']} organizing {row['event']}")
        print(f"Request Date: {request_date}")
        print(f"Cash Balance: ${current_cash:.2f}")
        print(f"Inventory Value: ${current_inventory:.2f}")

        # Process request via the multi-agent system
        request_with_date = f"{row['request']} (Date of request: {request_date})"
        try:
            response = handle_customer_request(request_with_date)
        except Exception as exc:
            response = f"Error: {exc}"

        # Update state
        report = generate_financial_report(request_date)
        current_cash = report["cash_balance"]
        current_inventory = report["inventory_value"]

        print(f"Response: {response}")
        print(f"Updated Cash: ${current_cash:.2f}")
        print(f"Updated Inventory: ${current_inventory:.2f}")

        results.append(
            {
                "request_id": idx + 1,
                "request_date": request_date,
                "cash_balance": current_cash,
                "inventory_value": current_inventory,
                "response": response,
            }
        )

        time.sleep(3)

    # Final report
    final_date = quote_requests_sample["request_date"].max().strftime("%Y-%m-%d")
    final_report = generate_financial_report(final_date)
    print("\n===== FINAL FINANCIAL REPORT =====")
    print(f"Final Cash: ${final_report['cash_balance']:.2f}")
    print(f"Final Inventory: ${final_report['inventory_value']:.2f}")

    # Save results
    pd.DataFrame(results).to_csv("test_results.csv", index=False)
    return results


if __name__ == "__main__":
    results = run_test_scenarios()
