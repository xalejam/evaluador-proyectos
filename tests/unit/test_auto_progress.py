from datetime import date, timedelta
import tempfile
from domain.services.seguimiento_operativo_service import OperationalTrackingService


def _service():
    tmp = tempfile.mktemp(suffix=".db")
    svc = OperationalTrackingService(tmp)
    svc.ensure_schema()
    return svc


def test_auto_progress_project_with_6_month_duration():
    today = date.today()
    start_dt = today - timedelta(days=90)
    end_dt = today + timedelta(days=90)
    svc = _service()
    progress = svc.calculate_auto_progress(start_dt, end_dt)
    assert 40 <= progress <= 60, f"Project at 50% of 180-day duration should show ~50%, not {progress}%"


def test_auto_progress_new_project_long_duration():
    today = date.today()
    start_dt = today - timedelta(days=1)
    end_dt = today + timedelta(days=240)
    svc = _service()
    progress = svc.calculate_auto_progress(start_dt, end_dt)
    assert 0 <= progress < 10, f"New long project should not show >10%, got {progress}%"


def test_auto_progress_past_end_date_returns_100():
    today = date.today()
    svc = _service()
    progress = svc.calculate_auto_progress(today - timedelta(days=200), today - timedelta(days=1))
    assert progress == 100
