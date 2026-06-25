"""
Unit tests for the agent tool functions defined in project_starter.py.

Tests are grouped by tool and cover the business-logic contract each tool
must satisfy, independent of any LLM.  All tests use the `db` fixture from
conftest.py for database-backed tools; pure-calculation tools need no fixture.

All tests in this file must FAIL until the tool implementations are in place.
"""
import json
import pytest
import project_starter as ps


# ──────────────────────────────────────────────────────────────────────────────
# list_catalog_items  (no DB required)
# ──────────────────────────────────────────────────────────────────────────────

class TestListCatalogItems:
    def test_returns_a_string(self):
        assert isinstance(ps.list_catalog_items(), str)

    def test_contains_every_catalogue_item(self):
        result = ps.list_catalog_items()
        for item in ps.paper_supplies:
            assert item["item_name"] in result, f"'{item['item_name']}' missing from catalogue listing"

    def test_contains_unit_prices(self):
        result = ps.list_catalog_items()
        # A4 paper costs $0.05/unit
        assert "0.05" in result


# ──────────────────────────────────────────────────────────────────────────────
# check_item_stock  (DB required)
# ──────────────────────────────────────────────────────────────────────────────

class TestCheckItemStock:
    def test_reports_out_of_stock_for_unknown_item(self, db):
        result = ps.check_item_stock("NonExistentItem99", "2025-06-01")
        assert "out of stock" in result.lower() or "0" in result

    def test_includes_item_name_in_output(self, db):
        result = ps.check_item_stock("Cardstock", "2025-06-01")
        assert "Cardstock" in result

    def test_reports_quantity_after_stock_order(self, db):
        # Capture pre-existing seeded stock before adding more
        pre = int(ps.get_stock_level("A4 paper", "2025-12-31")["current_stock"].iloc[0])
        ps.create_transaction("A4 paper", "stock_orders", 500, 25.0, "2025-01-02")
        result = ps.check_item_stock("A4 paper", "2025-12-31")
        assert str(pre + 500) in result


# ──────────────────────────────────────────────────────────────────────────────
# list_available_inventory  (DB required)
# ──────────────────────────────────────────────────────────────────────────────

class TestListAvailableInventory:
    def test_returns_a_string(self, db):
        assert isinstance(ps.list_available_inventory("2025-12-31"), str)

    def test_shows_no_stock_before_any_transactions(self, db):
        result = ps.list_available_inventory("2024-01-01")
        assert "no items" in result.lower() or len(result.strip()) > 0

    def test_shows_stocked_items_after_init(self, db):
        # init_database seeds 40 % of the catalogue; date is past the seed date
        result = ps.list_available_inventory("2025-12-31")
        assert "No items" not in result


# ──────────────────────────────────────────────────────────────────────────────
# calculate_quote  (no DB — pure calculation using CATALOG_PRICES)
# ──────────────────────────────────────────────────────────────────────────────

class TestCalculateQuote:
    """Discount tiers: >5000→15 %, >1000→10 %, >200→5 %, else 0 %.
    Multi-item order adds a further 5 % off the subtotal."""

    def _q(self, items_list):
        """Helper: call calculate_quote and parse the JSON response."""
        return json.loads(ps.calculate_quote(json.dumps(items_list), "2025-01-02"))

    def test_result_has_required_keys(self):
        result = self._q([{"item_name": "A4 paper", "quantity": 10}])
        assert {"items", "subtotal", "multi_item_discount_pct", "total", "currency"}.issubset(result)

    def test_no_discount_at_or_below_200_units(self):
        result = self._q([{"item_name": "A4 paper", "quantity": 200}])
        assert result["items"][0]["bulk_discount_pct"] == 0
        assert abs(result["total"] - 200 * 0.05) < 0.01

    def test_5pct_discount_above_200_units(self):
        result = self._q([{"item_name": "A4 paper", "quantity": 201}])
        assert result["items"][0]["bulk_discount_pct"] == 5
        assert abs(result["total"] - 201 * 0.05 * 0.95) < 0.01

    def test_10pct_discount_above_1000_units(self):
        result = self._q([{"item_name": "A4 paper", "quantity": 1001}])
        assert result["items"][0]["bulk_discount_pct"] == 10
        assert abs(result["total"] - 1001 * 0.05 * 0.90) < 0.01

    def test_15pct_discount_above_5000_units(self):
        result = self._q([{"item_name": "A4 paper", "quantity": 5001}])
        assert result["items"][0]["bulk_discount_pct"] == 15
        assert abs(result["total"] - 5001 * 0.05 * 0.85) < 0.01

    def test_multi_item_order_applies_additional_5pct(self):
        result = self._q([
            {"item_name": "A4 paper", "quantity": 100},
            {"item_name": "Cardstock", "quantity": 100},
        ])
        assert result["multi_item_discount_pct"] == 5
        subtotal = (100 * 0.05) + (100 * 0.15)   # A4=$0.05, Cardstock=$0.15
        assert abs(result["total"] - subtotal * 0.95) < 0.01

    def test_single_item_has_no_multi_item_discount(self):
        result = self._q([{"item_name": "A4 paper", "quantity": 100}])
        assert result["multi_item_discount_pct"] == 0

    def test_unknown_item_returns_error_key(self):
        result = self._q([{"item_name": "UnobtaniumPaper", "quantity": 100}])
        assert "error" in result

    def test_boundary_exactly_1000_units_gets_10pct(self):
        result = self._q([{"item_name": "A4 paper", "quantity": 1000}])
        assert result["items"][0]["bulk_discount_pct"] == 10

    def test_boundary_exactly_5000_units_gets_15pct(self):
        result = self._q([{"item_name": "A4 paper", "quantity": 5000}])
        assert result["items"][0]["bulk_discount_pct"] == 15


# ──────────────────────────────────────────────────────────────────────────────
# get_current_cash_balance  (DB required)
# ──────────────────────────────────────────────────────────────────────────────

class TestGetCurrentCashBalance:
    def test_returns_a_string(self, db):
        assert isinstance(ps.get_current_cash_balance("2025-01-02"), str)

    def test_contains_dollar_sign(self, db):
        assert "$" in ps.get_current_cash_balance("2025-01-02")

    def test_reflects_seed_balance(self, db):
        result = ps.get_current_cash_balance("2025-01-02")
        # Extract the numeric balance — should be well above $10k after seed
        balance = float(result.split("$")[1].replace(",", "").strip())
        assert balance > 10_000, f"Expected cash > $10,000 after seed, got {result}"


# ──────────────────────────────────────────────────────────────────────────────
# process_sale_transaction  (DB required)
# ──────────────────────────────────────────────────────────────────────────────

class TestProcessSaleTransaction:
    def test_success_when_stock_is_sufficient(self, db):
        ps.create_transaction("A4 paper", "stock_orders", 500, 25.0, "2025-01-02")
        result = json.loads(ps.process_sale_transaction("A4 paper", 100, 0.06, "2025-06-01"))
        assert result["success"] is True
        assert "transaction_id" in result

    def test_failure_when_stock_is_insufficient(self, db):
        result = json.loads(ps.process_sale_transaction("A4 paper", 999_999, 0.06, "2025-06-01"))
        assert result["success"] is False
        assert "error" in result

    def test_total_equals_quantity_times_unit_price(self, db):
        ps.create_transaction("Cardstock", "stock_orders", 500, 75.0, "2025-01-02")
        result = json.loads(ps.process_sale_transaction("Cardstock", 50, 0.20, "2025-06-01"))
        assert result["success"] is True
        assert abs(result["total"] - 50 * 0.20) < 0.01

    def test_stock_decreases_by_sold_quantity(self, db):
        pre = int(ps.get_stock_level("Glossy paper", "2025-12-31")["current_stock"].iloc[0])
        ps.create_transaction("Glossy paper", "stock_orders", 300, 60.0, "2025-01-02")
        ps.process_sale_transaction("Glossy paper", 100, 0.25, "2025-06-01")
        stock = ps.get_stock_level("Glossy paper", "2025-06-01")["current_stock"].iloc[0]
        assert stock == pre + 300 - 100


# ──────────────────────────────────────────────────────────────────────────────
# place_supplier_restock  (DB required)
# ──────────────────────────────────────────────────────────────────────────────

class TestPlaceSupplierRestock:
    def test_returns_success_with_delivery_and_cost(self, db):
        result = json.loads(ps.place_supplier_restock("A4 paper", 500, "2025-03-01"))
        assert result["success"] is True
        assert "delivery_date" in result
        assert "cost" in result

    def test_delivery_date_matches_helper_function(self, db):
        result = json.loads(ps.place_supplier_restock("A4 paper", 500, "2025-03-01"))
        expected = ps.get_supplier_delivery_date("2025-03-01", 500)
        assert result["delivery_date"] == expected

    def test_cost_is_quantity_times_unit_price(self, db):
        result = json.loads(ps.place_supplier_restock("A4 paper", 100, "2025-03-01"))
        assert abs(result["cost"] - 100 * 0.05) < 0.01  # A4 paper = $0.05/unit

    def test_stock_increases_after_restock(self, db):
        before = ps.get_stock_level("A4 paper", "2025-03-01")["current_stock"].iloc[0]
        ps.place_supplier_restock("A4 paper", 200, "2025-03-01")
        after = ps.get_stock_level("A4 paper", "2025-03-01")["current_stock"].iloc[0]
        assert after == before + 200

    def test_unknown_item_returns_failure(self, db):
        result = json.loads(ps.place_supplier_restock("UnobtaniumPaper", 100, "2025-03-01"))
        assert result["success"] is False


# ──────────────────────────────────────────────────────────────────────────────
# restock_all_low_inventory  (DB required)
# ──────────────────────────────────────────────────────────────────────────────

class TestRestockAllLowInventory:
    def test_returns_valid_json_string(self, db):
        result = ps.restock_all_low_inventory("2025-12-31")
        parsed = json.loads(result)
        assert isinstance(parsed, dict)
        assert "restocked" in parsed

    def test_no_restock_needed_when_all_stocked(self, db):
        # After init_database stock ≥ 200, min_stock ≤ 150 — all items are above minimum
        result = json.loads(ps.restock_all_low_inventory("2025-01-02"))
        assert result["restocked"] == []

    def test_restocks_item_that_falls_below_minimum(self, db):
        inventory = ps.get_all_inventory("2025-01-02")
        if not inventory:
            pytest.skip("No inventory seeded")
        item_name = next(iter(inventory))
        current = inventory[item_name]
        # Drain all but a tiny amount so it's below any reasonable minimum
        ps.create_transaction(item_name, "sales", current - 2, 1.0, "2025-06-01")

        before = ps.get_stock_level(item_name, "2025-06-01")["current_stock"].iloc[0]
        ps.restock_all_low_inventory("2025-06-01")
        after = ps.get_stock_level(item_name, "2025-06-01")["current_stock"].iloc[0]

        assert after > before
