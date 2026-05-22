from unittest.mock import MagicMock, patch

import pytest

from domain.exceptions import ValidationError
from domain.services.viability_service import ViabilityService


def _make_svc():
    """Create a ViabilityService with a temp in-memory-style db path."""
    return ViabilityService(db_path=":memory:")


def test_approve_project_below_threshold_raises_validation_error():
    svc = _make_svc()
    inputs = {"name": "Test Project", "country": "MX", "owner": "TST"}
    calc_results = {"viability_score": 60}
    with patch("domain.services.viability_service.load_app_config", return_value={"approval_threshold": 80}):
        with pytest.raises(ValidationError):
            svc.approve_project(
                inputs=inputs,
                calc_results=calc_results,
                loop_url="https://example.com",
                author="tester",
                project_id=None,
                delivery_team=None,
            )


def test_approve_project_at_threshold_succeeds():
    svc = _make_svc()
    inputs = {"name": "Test Project", "country": "MX", "owner": "TST"}
    calc_results = {"viability_score": 80}

    mock_calculator = MagicMock()
    mock_calculator.create_project.return_value = ("MX-TST-0001", calc_results)

    mock_excel_manager = MagicMock()
    mock_excel_manager.project_exists.return_value = False

    with patch("domain.services.viability_service.load_app_config", return_value={"approval_threshold": 80}):
        with patch("domain.services.viability_service.st") as mock_st:
            mock_st.session_state.calculator = mock_calculator
            mock_st.session_state.excel_manager = mock_excel_manager
            with patch("domain.services.viability_service.sync_to_use_case_matrix"):
                with patch("domain.services.viability_service.get_sqlite_conn"):
                    with patch("domain.services.viability_service.ensure_schema"):
                        with patch.object(svc.project_repo, "update_status"):
                            with patch.object(svc.evaluation_repo, "insert_snapshot"):
                                # Should not raise
                                result = svc.approve_project(
                                    inputs=inputs,
                                    calc_results=calc_results,
                                    loop_url="https://example.com",
                                    author="tester",
                                    project_id=None,
                                    delivery_team=None,
                                )
                                assert result == "MX-TST-0001"
