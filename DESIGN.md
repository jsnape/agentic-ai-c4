# Beaver's Choice Paper Company — Multi-Agent System Design

## Overview

The system handles customer inquiries end-to-end using five specialised agents
coordinated by a central orchestrator. All inputs and outputs are text-based.
The agents share a SQLite database and a product catalogue defined in code.

---

## Agent Roster (≤ 5 agents)

| Agent | Role |
|---|---|
| **Orchestrator** | Receives every customer request, decides the workflow, calls sub-agents in sequence, and compiles the final customer-facing response. |
| **Inventory Agent** | Maps natural-language item names to exact catalogue entries and checks current stock levels. |
| **Quoting Agent** | Looks up historical quotes for context, then calculates an itemised price with tiered bulk discounts. |
| **Fulfillment Agent** | Verifies the company cash position and records confirmed sale transactions in the database. |
| **Supplier Agent** | Places restock orders with the supplier for any item whose inventory has fallen below its minimum threshold. |

---

## Tool Roster

| Tool | Owner Agent | Purpose |
|---|---|---|
| `list_catalog_items` | Inventory | Returns every item name and unit price in the catalogue. |
| `check_item_stock` | Inventory | Returns the current stock level for one named item as of a given date. |
| `list_available_inventory` | Inventory | Returns all items that have stock > 0 on a given date. |
| `get_similar_quotes` | Quoting | Searches historical quotes by keyword for pricing benchmarks. |
| `calculate_quote` | Quoting | Applies tiered bulk discounts and returns an itemised quote total. |
| `get_current_cash_balance` | Fulfillment | Returns the company's net cash position on a given date. |
| `process_sale_transaction` | Fulfillment | Writes a sales record to the database after verifying sufficient stock. |
| `place_supplier_restock` | Supplier | Places a single-item purchase order; returns cost and delivery date. |
| `restock_all_low_inventory` | Supplier | Scans every tracked item and auto-restocks those below minimum levels. |

---

## Bulk Discount Policy

Applied automatically inside `calculate_quote`:

| Units per line item | Discount |
|---|---|
| > 5 000 | 15 % |
| > 1 000 | 10 % |
| > 200 | 5 % |
| ≤ 200 | 0 % |

Orders with **more than one valid line item** receive an additional **5 % order-level discount** on the subtotal.

---

## System Architecture

```mermaid
graph TD
    Customer([Customer Request])
    Customer --> Orchestrator

    subgraph Agents
        Orchestrator(["🎯 Orchestrator\n(Chief Operations Officer)"])
        Inventory(["📦 Inventory Agent"])
        Quoting(["💰 Quoting Agent"])
        Fulfillment(["✅ Fulfillment Agent"])
        Supplier(["🚚 Supplier Agent"])
    end

    subgraph InventoryTools["Inventory Tools"]
        T1["list_catalog_items"]
        T2["check_item_stock"]
        T3["list_available_inventory"]
    end

    subgraph QuotingTools["Quoting Tools"]
        T4["get_similar_quotes"]
        T5["calculate_quote"]
    end

    subgraph FulfillmentTools["Fulfillment Tools"]
        T6["get_current_cash_balance"]
        T7["process_sale_transaction"]
    end

    subgraph SupplierTools["Supplier Tools"]
        T8["place_supplier_restock"]
        T9["restock_all_low_inventory"]
    end

    Orchestrator -->|"1. Check availability"| Inventory
    Orchestrator -->|"2. Generate quote"| Quoting
    Orchestrator -->|"3. Record sale"| Fulfillment
    Orchestrator -->|"4. Restock check"| Supplier

    Inventory --- T1 & T2 & T3
    Quoting --- T4 & T5
    Fulfillment --- T6 & T7
    Supplier --- T8 & T9

    DB[(SQLite Database\ntransactions\ninventory\nquotes)]
    T2 & T3 & T5 & T6 & T7 & T8 & T9 --> DB

    Orchestrator --> Response([Customer Response])
```

---

## Request Processing Flow

```mermaid
sequenceDiagram
    actor Customer
    participant ORC as Orchestrator
    participant INV as Inventory Agent
    participant QUO as Quoting Agent
    participant FUL as Fulfillment Agent
    participant SUP as Supplier Agent
    participant DB  as SQLite DB

    Customer->>ORC: Request (items, quantities, date)

    ORC->>INV: "Check availability for [request]"
    INV->>DB: list_catalog_items()
    INV->>DB: check_item_stock(item, date) × N
    INV-->>ORC: Exact catalog names + stock levels

    alt Item out of stock
        ORC->>SUP: "Restock [item] urgently"
        SUP->>DB: place_supplier_restock(item, qty, date)
        SUP-->>ORC: Delivery date confirmed
        ORC->>INV: Re-check stock after restock
    end

    ORC->>QUO: "Quote [items + quantities + date]"
    QUO->>DB: get_similar_quotes(keywords)
    QUO->>QUO: calculate_quote(items_json, date)
    QUO-->>ORC: Itemised quote with totals & discounts

    ORC->>FUL: "Record sale [items + prices + date]"
    FUL->>DB: get_current_cash_balance(date)
    FUL->>DB: process_sale_transaction(items_json, date)
    FUL-->>ORC: Transaction IDs + confirmation

    ORC->>SUP: "Restock any low items after sale"
    SUP->>DB: restock_all_low_inventory(date)
    SUP-->>ORC: Items restocked + delivery dates

    ORC-->>Customer: Quote breakdown · Total · Order # · Delivery ETA
```

---

## Inventory Reorder Logic

```mermaid
flowchart TD
    A[After every sale] --> B{current_stock < min_stock_level?}
    B -- No --> C[No action needed]
    B -- Yes --> D[Calculate restock_qty = min_stock_level × 3]
    D --> E[place_supplier_restock]
    E --> F{Delivery lead time}
    F -- "≤ 10 units" --> G[Same day]
    F -- "11–100 units" --> H[+1 day]
    F -- "101–1000 units" --> I[+4 days]
    F -- "> 1000 units" --> J[+7 days]
    G & H & I & J --> K[Record stock_order transaction]
    K --> L[Notify Orchestrator of delivery date]
```

---

## Data Model (Key Tables)

```mermaid
erDiagram
    INVENTORY {
        string item_name PK
        string category
        float unit_price
        int current_stock
        int min_stock_level
    }
    TRANSACTIONS {
        int id PK
        string item_name FK
        string transaction_type
        int units
        float price
        string transaction_date
    }
    QUOTES {
        int request_id PK
        float total_amount
        string quote_explanation
        string job_type
        string order_size
        string event_type
        string order_date
    }
    QUOTE_REQUESTS {
        int id PK
        string job
        string need_size
        string event
        string request
        string request_date
    }

    INVENTORY ||--o{ TRANSACTIONS : "tracked via"
    QUOTE_REQUESTS ||--|| QUOTES : "fulfilled by"
```

---

## Design Decisions

### Why smolagents?
`smolagents` is chosen as the orchestration framework because:
- Its `ToolCallingAgent` + `ManagedAgent` pattern maps cleanly to a hierarchical multi-agent design.
- It integrates directly with any OpenAI-compatible API via `OpenAIServerModel`.
- Tools are defined with simple Python `@tool` decorators — no boilerplate schemas required.

### Why five agents (not fewer)?
Separating Inventory, Quoting, Fulfillment, and Supplier concerns keeps each agent's tool set small and its system prompt focused. A single monolithic agent would struggle to reliably follow a four-step workflow within a single ReAct loop.

### Item name matching
Customers rarely use exact catalogue names. The Inventory Agent is given the full catalogue on every call and instructed to identify the closest matching canonical name before any stock check or quote is generated. This prevents silent misses where an item exists in stock under a slightly different name.

### Restock quantity = 3 × minimum
Ordering three times the minimum threshold avoids constant reordering while keeping the order size modest enough for next-day delivery on most items.
