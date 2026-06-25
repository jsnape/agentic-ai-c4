"""
Acceptance tests for run_test_scenarios().

These verify the observable contract of the end-to-end test harness
without making real LLM calls.  handle_customer_request is patched to a
stub so the tests are fast, isolated, and repeatable.

All tests in this file must FAIL until the full implementation is complete.
"""
import shutil
import time
import pytest
import pandas as pd
from pathlib import Path
from unittest.mock import patch
from sqlalchemy import create_engine
import project_starter as ps

PROJECT_ROOT = Path(__file__).parent.parent
STUB = "Thank you for your inquiry. Here is your quote."


@pytest.fixture
def acceptance_env(tmp_path, monkeypatch):
    """
    Isolated test environment for run_test_scenarios().

    - Copies CSV data files into a temp directory.
    - Changes the working directory so relative file I/O uses the temp dir.
    - Replaces the module-level db_engine with an in-memory SQLite database.
    - Suppresses time.sleep so the test suite runs quickly.
    """
    for name in ("quote_requests.csv", "quotes.csv", "quote_requests_sample.csv"):
        shutil.copy(PROJECT_ROOT / name, tmp_path / name)
    monkeypatch.chdir(tmp_path)
    engine = create_engine("sqlite:///:memory:")
    monkeypatch.setattr(ps, "db_engine", engine)
    monkeypatch.setattr(time, "sleep", lambda _: None)
    yield tmp_path
    engine.dispose()


class TestRunTestScenariosContract:
    """Every method is an acceptance criterion for run_test_scenarios()."""

    def test_returns_a_list(self, acceptance_env):
        with patch.object(ps, "handle_customer_request", return_value=STUB):
            result = ps.run_test_scenarios()
        assert isinstance(result, list)

    def test_processes_all_20_requests(self, acceptance_env):
        with patch.object(ps, "handle_customer_request", return_value=STUB):
            result = ps.run_test_scenarios()
        assert len(result) == 20

    def test_each_result_has_required_fields(self, acceptance_env):
        required = {"request_id", "request_date", "cash_balance", "inventory_value", "response"}
        with patch.object(ps, "handle_customer_request", return_value=STUB):
            result = ps.run_test_scenarios()
        for row in result:
            missing = required - row.keys()
            assert not missing, f"Result missing fields: {missing}"

    def test_responses_are_non_empty_strings(self, acceptance_env):
        with patch.object(ps, "handle_customer_request", return_value=STUB):
            result = ps.run_test_scenarios()
        for row in result:
            assert isinstance(row["response"], str) and len(row["response"]) > 0

    def test_cash_balance_is_numeric(self, acceptance_env):
        with patch.object(ps, "handle_customer_request", return_value=STUB):
            result = ps.run_test_scenarios()
        for row in result:
            assert isinstance(row["cash_balance"], (int, float))

    def test_inventory_value_is_numeric(self, acceptance_env):
        with patch.object(ps, "handle_customer_request", return_value=STUB):
            result = ps.run_test_scenarios()
        for row in result:
            assert isinstance(row["inventory_value"], (int, float))

    def test_writes_test_results_csv(self, acceptance_env):
        with patch.object(ps, "handle_customer_request", return_value=STUB):
            ps.run_test_scenarios()
        assert (acceptance_env / "test_results.csv").exists()

    def test_csv_has_one_row_per_request(self, acceptance_env):
        with patch.object(ps, "handle_customer_request", return_value=STUB):
            ps.run_test_scenarios()
        df = pd.read_csv(acceptance_env / "test_results.csv")
        assert len(df) == 20

    def test_requests_processed_in_date_order(self, acceptance_env):
        with patch.object(ps, "handle_customer_request", return_value=STUB):
            result = ps.run_test_scenarios()
        dates = [row["request_date"] for row in result]
        assert dates == sorted(dates)

    def test_handle_customer_request_called_once_per_request(self, acceptance_env):
        with patch.object(ps, "handle_customer_request", return_value=STUB) as mock_fn:
            ps.run_test_scenarios()
        assert mock_fn.call_count == 20
