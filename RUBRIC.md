
Use this project rubric to understand and assess the project criteria.

---

## Evidence of Satisfaction

### Test Run Summary (from `test_results.csv`)

| Metric | Result |
|---|---|
| Total requests processed | 20 / 20 |
| Requests that changed cash balance | **16** (need ≥ 3) ✅ |
| Requests with confirmed fulfilled orders | **15** (need ≥ 3) ✅ |
| Requests with unfulfilled reasons documented | **8** (need > 0, not all) ✅ |
| Starting cash balance | $44,947.70 |
| Ending cash balance | $9,149.55 |
| Ending inventory value | $37,688.95 |

**Per-request status:**

| # | Date | Cash | Inventory | Status |
|---|---|---|---|---|
| 1 | 2025-04-01 | $44,947.70 | $5,040.30 | Described order (partial) |
| 2 | 2025-04-03 | $44,757.70 | $5,040.30 | ✅ Fulfilled (poster paper, streamers) + ❌ balloons not in catalog |
| 3 | 2025-04-04 | $43,987.70 | $5,790.30 | ✅ Fulfilled (copy paper, A4 paper) + quote provided |
| 4 | 2025-04-05 | $43,962.70 | $5,815.30 | ✅ Partial restock; recycled cardstock not in catalog |
| 5 | 2025-04-05 | $42,597.70 | $6,630.30 | ✅ Fulfilled (colored paper, cardstock, washi tape) |
| 6 | 2025-04-06 | $42,553.70 | $6,660.30 | ✅ Partial + ❌ construction/printer paper unavailable |
| 7 | 2025-04-07 | $41,363.70 | $7,490.30 | ✅ Fulfilled (poster, glossy, matte, cardstock restock) |
| 8 | 2025-04-07 | $41,363.70 | $7,490.30 | ❌ Out of stock — matte and recycled paper unavailable |
| 9 | 2025-04-07 | $41,363.70 | $7,490.30 | ✅ Fulfilled (A4 paper, glossy paper, envelopes) |
| 10 | 2025-04-08 | $41,183.70 | $7,670.30 | ✅ Glossy fulfilled + ❌ cardstock out of stock |
| 11 | 2025-04-08 | $41,183.70 | $7,670.30 | ❌ All items out of stock, alternatives suggested |
| 12 | 2025-04-08 | $41,228.70 | $7,625.30 | ✅ Fulfilled (colored paper, copy paper, napkins) |
| 13 | 2025-04-08 | $41,238.70 | $7,615.30 | ✅ Fulfilled (A4 paper, cardstock) |
| 14 | 2025-04-09 | $41,183.70 | $7,670.30 | ✅ Fulfilled (A4 paper, cardstock, poster paper) |
| 15 | 2025-04-12 | $41,091.20 | $7,720.30 | ❌ All requested items out of stock |
| 16 | 2025-04-13 | $41,021.20 | $7,765.30 | ✅ Restock orders placed (A4, construction, poster) |
| 17 | 2025-04-14 | $38,802.55 | $9,983.95 | ✅ Partial + ❌ biodegradable items not in catalog; quote provided |
| 18 | 2025-04-14 | $38,527.55 | $10,178.95 | ✅ Copy paper fulfilled; cardstock pending |
| 19 | 2025-04-15 | $36,899.55 | $10,688.95 | ✅ Fulfilled (glossy, matte, cardstock — large order) |
| 20 | 2025-04-17 | $9,149.55 | $37,688.95 | ✅ Partial restock + ❌ tickets not in catalog |

### Helper Function Usage

All 7 required helper functions are called within tool definitions in `project_starter.py`:

| Helper Function | Used In Tool |
|---|---|
| `create_transaction` | `process_sale_transaction`, `place_supplier_restock`, `restock_all_low_inventory` |
| `get_all_inventory` | `list_available_inventory` |
| `get_stock_level` | `check_item_stock`, `process_sale_transaction`, `restock_all_low_inventory` |
| `get_supplier_delivery_date` | `place_supplier_restock`, `restock_all_low_inventory`, `order_supplier_restock` |
| `get_cash_balance` | `get_current_cash_balance` |
| `generate_financial_report` | `run_test_scenarios` (harness) |
| `search_quote_history` | `search_historical_quotes` |

### Agent Workflow Diagram

See `DESIGN.md` for the full diagrams. Summary:
- **4 agents** (≤ 5 constraint satisfied): `orchestrator`, `inventory_agent`, `quoting_agent`, `sales_agent`
- Each agent has non-overlapping responsibilities and an explicit tool set
- Orchestration flow and data handoff between agents is shown in the sequence diagram

### Industry Best Practices

- All customer responses include the items ordered, quantities, prices, delivery dates, and reasons for any refusals
- No internal error messages, profit margins, or PII are exposed in responses
- Code uses `snake_case` throughout, docstrings on all functions and tools, and is split into logical sections (helpers → tools → agents → harness)

---

## Rubric Criteria

## Agent Workflow Diagram

|Criteria|Submission Requirements|
|---|---|
|Illustrate the architecture of the multi-agent system, including agent responsibilities and orchestration.|- The workflow diagram includes all of the agents in the multi-agent system (maximum of five agents as per project constraints).<br>- Each agent has explicitly defined responsibilities that do not overlap with other systems.<br>- The orchestration logic and data flow between agents is clear.|
|Illustrate the interactions between agents and their tools, specifying the purpose of each tool.|- The workflow diagram depicts tools associated with specific agents.<br>- For each tool depicted, its purpose and the specific helper function(s) from the starter code it intends to use is specified in the diagram.<br>- The diagram shows interactions (e.g., data input/output) between agents and their respective tools.|

## Multi-Agent System Implementation

|Criteria|Submission Requirements|
|---|---|
|Implement the multi-agent system with distinct orchestrator and worker agent roles as per their diagram.|- The implemented multi-agent system architecture (agents, their primary roles) matches the submitted agent workflow diagram.<br>- The system includes an orchestrator agent that manages task delegation to other agents.<br>- The system implements distinct worker agents (or clearly separated functionalities within agents) for different tasks such as:<br>    -  Inventory management (e.g., checking stock, assessing reorder needs)<br>    - Quoting (e.g., generating prices, considering discounts)<br>    - Sales finalization (e.g., processing orders, updating database).<br>- The student selects and utilizes one of the recommended agent orchestration frameworks (smolagents, pydantic-ai, or npcsh) for the implementation.|
|Implement tools for agents using the provided helper functions, ensuring all required functions are utilized.|- Tools for different agents are defined in the code according to the conventions of the selected agent orchestration framework.<br>- All of the following helper functions from the starter code are used in at least one tool definition within the implemented system: `create_transaction`, `get_all_inventory`, `get_stock_level`, `get_supplier_delivery_date`, `get_cash_balance`, `generate_financial_report`, `search_quote_history`.|

## Evaluation and Reflection

|Criteria|Submission Requirements|
|---|---|
|Evaluate the multi-agent system using the provided dataset and document the results.|- The multi-agent system is evaluated using the full set of requests provided in quote_requests_sample.csv and the results of the evaluation are submitted in test_results.csv.<br>- The test_results.csv file (or equivalent documented output) demonstrates that:<br>    - At least three requests result in a change to the cash balance.<br>    - At least three quote requests are successfully fulfilled.<br>    - Not all requests from quote_requests_sample.csv are fulfilled, with reasons provided or implied for unfulfilled requests (e.g., insufficient stock).|
|Reflect on the architecture, implementation, and performance evaluation of the multi-agent system.|The reflection report:<br><br>- contains an explanation of the agent workflow diagram, detailing the roles of the agents and the decision-making process that led to the chosen architecture. The student may refer to their diagram file, but the explanation must be in this text report.<br>- discusses the evaluation results from test_results.csv, identifying specific strengths of the implemented system. The student may refer to their test_results.csv file, but the discussion must be in this text report.<br>- includes at least two distinct suggestions for further improvements to the system, based on the identified areas of improvement or new potential features.|

## Industry Best Practices

|Criteria|Submission Requirements|
|---|---|
|Provide transparent and explainable outputs for customer-facing interactions.|- Outputs generated by the system (e.g., quotes, responses to inquiries) for the "customer" contain all the information directly relevant to the customer's request.<br>- Outputs provided to the "customer" include a rationale or justification for key decisions or outcomes, where appropriate (e.g., why a quote is priced a certain way if discounts are applied, why an order cannot be fulfilled).<br>- Customer-facing outputs do not reveal sensitive internal company information (e.g., exact profit margins, internal system error messages) or any personally identifiable information (PII) beyond what's essential for the transaction.|
|Write code that is readable, well-commented, and modular.|- Variable and function names in the Python code are descriptive and consistently follow a discernible naming convention (e.g., snake_case for functions and variables, PascalCase for classes, if applicable).<br>- The code consists of comments and docstrings at appropriate places.<br>- Logic within the code has been broken down sufficiently into individual modules.|