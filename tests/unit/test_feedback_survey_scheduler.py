from datetime import datetime

from infra.feedback_survey_scheduler import build_send_at, register_feedback_survey


def test_build_send_at_adds_months_to_baseline():
    base = datetime(2026, 1, 15, 10, 0, 0)

    result = build_send_at(base, 3)

    assert result == datetime(2026, 4, 15, 10, 0, 0)


def test_register_feedback_survey_inserts_row(monkeypatch):
    calls = []

    class DummyConn:
        def execute(self, sql, params=()):
            calls.append((sql, params))
            return self

        def commit(self):
            return None

        def close(self):
            return None

        def __enter__(self):
            return self

        def __exit__(self, exc_type, exc, tb):
            self.close()

    monkeypatch.setattr("infra.feedback_survey_scheduler.get_connection", lambda local_path=None: DummyConn())
    monkeypatch.setattr("infra.feedback_survey_scheduler._append_log", lambda *args, **kwargs: None)

    result = register_feedback_survey(
        project_id="PRJ-100",
        project_name="Proyecto demo",
        recipients="user@example.com",
        survey_link="https://forms.example.com/abc",
        send_after_months=1,
        send_at=datetime(2026, 1, 15, 10, 0, 0),
    )

    assert result is True
    assert calls
    assert "feedback_survey_schedules" in calls[0][0]
    assert calls[0][1][0] == "PRJ-100"
    assert calls[0][1][1] == "Proyecto demo"
