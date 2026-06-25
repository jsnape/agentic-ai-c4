"""
Tests for the pure helper functions in project_starter.py.

These tests cover two categories:
 - Pure functions that need no database (delivery date, inventory generation).
 - Database-backed helpers that operate against the in-memory `db` fixture.
"""
import project_starter as ps


# ---------------------------------------------------------------------------
# get_supplier_delivery_date — pure calculation, no DB needed
# ---------------------------------------------------------------------------

class TestGetSupplierDeliveryDate:
    """Delivery lead-time is determined entirely by quantity; no DB required."""

    def test_up_to_ten_units_same_day(self):
        assert ps.get_supplier_delivery_date("2025-03-10", 10) == "2025-03-10"

    def test_eleven_units_one_day(self):
        assert ps.get_supplier_delivery_date("2025-03-10", 11) == "2025-03-11"

    def test_one_hundred_units_one_day(self):
        assert ps.get_supplier_delivery_date("2025-03-10", 100) == "2025-03-11"

    def test_one_hundred_one_units_four_days(self):
        assert ps.get_supplier_delivery_date("2025-03-10", 101) == "2025-03-14"

    def test_one_thousand_units_four_days(self):
        assert ps.get_supplier_delivery_date("2025-03-10", 1000) == "2025-03-14"

    def test_over_one_thousand_units_seven_days(self):
        assert ps.get_supplier_delivery_date("2025-03-10", 1001) == "2025-03-17"

    def test_returns_string(self):
        result = ps.get_supplier_delivery_date("2025-06-01", 50)
        assert isinstance(result, str)

    def test_iso_date_format(self):
        result = ps.get_supplier_delivery_date("2025-06-01", 50)
        # Must be parseable as YYYY-MM-DD
        from datetime import datetime
        datetime.strptime(result, "%Y-%m-%d")  # raises if format is wrong


# ---------------------------------------------------------------------------
# generate_sample_inventory — pure function with controlled randomness
# ---------------------------------------------------------------------------

class TestGenerateSampleInventory:
    """generate_sample_inventory is deterministic given a fixed seed."""

    def test_item_count_matches_coverage(self):
        df = ps.generate_sample_inventory(ps.paper_supplies, coverage=0.4, seed=137)
        assert len(df) == int(len(ps.paper_supplies) * 0.4)

    def test_required_columns_present(self):
        df = ps.generate_sample_inventory(ps.paper_supplies)
        required = {"item_name", "category", "unit_price", "current_stock", "min_stock_level"}
        assert required.issubset(df.columns)

    def test_stock_within_expected_range(self):
        df = ps.generate_sample_inventory(ps.paper_supplies, seed=1)
        assert df["current_stock"].between(200, 800).all()

    def test_min_stock_within_expected_range(self):
        df = ps.generate_sample_inventory(ps.paper_supplies, seed=1)
        assert df["min_stock_level"].between(50, 150).all()

    def test_reproducible_with_same_seed(self):
        df1 = ps.generate_sample_inventory(ps.paper_supplies, seed=42)
        df2 = ps.generate_sample_inventory(ps.paper_supplies, seed=42)
        assert df1.equals(df2)

    def test_different_seeds_differ(self):
        df1 = ps.generate_sample_inventory(ps.paper_supplies, seed=1)
        df2 = ps.generate_sample_inventory(ps.paper_supplies, seed=2)
        assert not df1.equals(df2)


# ---------------------------------------------------------------------------
# Database-backed helpers (require the `db` fixture from conftest.py)
# ---------------------------------------------------------------------------

class TestGetCashBalance:

    def test_initial_balance_is_positive(self, db):
        # The seed transaction uses ISO datetime "2025-01-01T00:00:00"; query
        # with a date-only string "2025-01-01" falls before it in SQLite's
        # lexicographic comparison, so use the day after to include the seed.
        balance = ps.get_cash_balance("2025-01-02")
        assert balance > 0

    def test_balance_is_float(self, db):
        balance = ps.get_cash_balance("2025-01-01")
        assert isinstance(balance, float)

    def test_sale_increases_balance(self, db):
        before = ps.get_cash_balance("2025-06-01")
        ps.create_transaction("A4 paper", "sales", 10, 1.00, "2025-06-01")
        after = ps.get_cash_balance("2025-06-01")
        assert after == before + 1.00

    def test_stock_order_decreases_balance(self, db):
        before = ps.get_cash_balance("2025-06-01")
        ps.create_transaction("A4 paper", "stock_orders", 100, 5.00, "2025-06-01")
        after = ps.get_cash_balance("2025-06-01")
        assert after == before - 5.00


class TestCreateTransaction:

    def test_returns_integer_id(self, db):
        txn_id = ps.create_transaction("Cardstock", "stock_orders", 50, 7.50, "2025-02-01")
        assert isinstance(txn_id, int)
        assert txn_id > 0

    def test_each_call_returns_unique_id(self, db):
        id1 = ps.create_transaction("Cardstock", "stock_orders", 50, 7.50, "2025-02-01")
        id2 = ps.create_transaction("Cardstock", "stock_orders", 50, 7.50, "2025-02-01")
        assert id1 != id2


class TestGetStockLevel:

    def test_stock_increases_after_order(self, db):
        ps.create_transaction("Glossy paper", "stock_orders", 200, 40.00, "2025-03-01")
        df = ps.get_stock_level("Glossy paper", "2025-03-01")
        assert df["current_stock"].iloc[0] >= 200

    def test_stock_decreases_after_sale(self, db):
        ps.create_transaction("Glossy paper", "stock_orders", 300, 60.00, "2025-03-01")
        stock_before = ps.get_stock_level("Glossy paper", "2025-03-01")["current_stock"].iloc[0]
        ps.create_transaction("Glossy paper", "sales", 50, 25.00, "2025-03-02")
        stock_after = ps.get_stock_level("Glossy paper", "2025-03-02")["current_stock"].iloc[0]
        assert stock_after == stock_before - 50

    def test_returns_dataframe_with_correct_columns(self, db):
        df = ps.get_stock_level("A4 paper", "2025-01-01")
        assert "current_stock" in df.columns


class TestGetAllInventory:

    def test_returns_dict(self, db):
        result = ps.get_all_inventory("2025-12-31")
        assert isinstance(result, dict)

    def test_initialised_items_in_inventory(self, db):
        result = ps.get_all_inventory("2025-12-31")
        assert len(result) > 0

    def test_sold_out_item_excluded(self, db):
        # Order 10 units of an item that doesn't exist yet, then sell all 10.
        ps.create_transaction("Test paper", "stock_orders", 10, 1.00, "2025-05-01")
        ps.create_transaction("Test paper", "sales", 10, 2.00, "2025-05-02")
        result = ps.get_all_inventory("2025-05-02")
        assert "Test paper" not in result
