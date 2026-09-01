"""Helpers para registrar y probar encuestas de feedback desde la app."""

from __future__ import annotations

import os
import smtplib
from datetime import datetime
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText

from infra.db.adapter import PLACEHOLDER, IS_CLOUD, get_connection


def build_send_at(base_date: datetime | None, send_after_months: int) -> datetime:
    """Calcula la fecha de envío sumando meses a una fecha base."""
    base = base_date or datetime.utcnow()
    year = base.year + (base.month - 1 + send_after_months) // 12
    month = (base.month - 1 + send_after_months) % 12 + 1
    day = min(base.day, 28)
    return datetime(year, month, day, base.hour, base.minute, base.second)


def _append_log(message: str) -> None:
    log_dir = "logs"
    os.makedirs(log_dir, exist_ok=True)
    with open(os.path.join(log_dir, "feedback_survey_scheduler.log"), "a", encoding="utf-8") as handle:
        handle.write(f"{datetime.utcnow().isoformat()} - {message}\n")


def register_feedback_survey(
    project_id: str,
    project_name: str,
    recipients: str,
    survey_link: str,
    send_after_months: int = 1,
    send_at: datetime | None = None,
) -> bool:
    """Registra una invitación de encuesta para un proyecto."""
    try:
        base_time = send_at or datetime.utcnow()
        effective_send_at = build_send_at(base_time, send_after_months)
        with get_connection() as conn:
            placeholders = ", ".join([PLACEHOLDER] * 7)
            conn.execute(
                f"""
                INSERT INTO feedback_survey_schedules (
                    project_id,
                    project_name,
                    recipients,
                    survey_link,
                    send_after_months,
                    send_at,
                    status
                ) VALUES ({placeholders})
                """,
                (
                    project_id,
                    project_name,
                    recipients,
                    survey_link,
                    send_after_months,
                    effective_send_at,
                    "pending",
                ),
            )
            conn.commit()
        _append_log(f"Registered survey for project {project_id} at {effective_send_at}")
        return True
    except Exception as exc:  # pragma: no cover - logging path
        _append_log(f"Failed to register survey for project {project_id}: {exc}")
        return False


def _parse_send_at(value) -> datetime | None:
    if value is None:
        return None
    if isinstance(value, datetime):
        return value
    if isinstance(value, str):
        text = value.replace("Z", "+00:00")
        try:
            return datetime.fromisoformat(text)
        except ValueError:
            try:
                return datetime.strptime(text, "%Y-%m-%d %H:%M:%S")
            except ValueError:
                return None
    return None


def _send_smtp_email(
    smtp_host: str,
    smtp_port: int,
    smtp_user: str,
    smtp_password: str,
    from_email: str,
    to_emails: list[str],
    subject: str,
    body: str,
) -> None:
    message = MIMEMultipart()
    message["From"] = from_email
    message["To"] = ", ".join(to_emails)
    message["Subject"] = subject
    message.attach(MIMEText(body, "plain", "utf-8"))

    if smtp_port == 465:
        server = smtplib.SMTP_SSL(smtp_host, smtp_port)
    else:
        server = smtplib.SMTP(smtp_host, smtp_port)
    try:
        if smtp_port != 465:
            server.starttls()
        server.login(smtp_user, smtp_password)
        server.sendmail(from_email, to_emails, message.as_string())
    finally:
        server.quit()


def send_pending_feedback_surveys(
    smtp_host: str | None = None,
    smtp_port: int | None = None,
    smtp_user: str | None = None,
    smtp_password: str | None = None,
    from_email: str | None = None,
) -> int:
    """Envía las encuestas pendientes cuyo momento de envío ya llegó."""
    smtp_host = smtp_host or os.getenv("SMTP_HOST", "")
    smtp_port = smtp_port or int(os.getenv("SMTP_PORT", "587"))
    smtp_user = smtp_user or os.getenv("SMTP_USER", "")
    smtp_password = smtp_password or os.getenv("SMTP_PASSWORD", "")
    from_email = from_email or os.getenv("SMTP_FROM_EMAIL", smtp_user)

    if not smtp_host or not smtp_user or not smtp_password:
        _append_log("SMTP settings are incomplete; skipping pending surveys")
        return 0

    try:
        with get_connection() as conn:
            rows = conn.execute(
                "SELECT id, project_id, project_name, recipients, survey_link, send_at FROM feedback_survey_schedules WHERE status = %s",
                ("pending",),
            ).fetchall()
    except Exception as exc:
        _append_log(f"Failed to fetch pending surveys: {exc}")
        return 0

    if not rows:
        _append_log(f"No pending surveys found. Backend: {'cloud' if IS_CLOUD else 'local sqlite'}")
        return 0

    sent_count = 0
    now = datetime.utcnow()
    for row in rows:
        try:
            send_at = _parse_send_at(row["send_at"] if isinstance(row, dict) else row[5])
            if send_at is not None and send_at > now:
                continue

            recipients = [
                item.strip()
                for item in (row["recipients"] if isinstance(row, dict) else row[3]).split(",")
                if item.strip()
            ]
            if not recipients:
                raise ValueError("No recipients configured")

            project_name = row["project_name"] if isinstance(row, dict) else row[2]
            survey_link = row["survey_link"] if isinstance(row, dict) else row[4]
            subject = f"Encuesta de feedback para {project_name or 'tu proyecto'}"
            body = (
                "Hola,\n\n"
                f"Te invitamos a completar la encuesta de feedback para el proyecto {project_name or 'seleccionado'}.\n"
                f"ID del proyecto: {row['project_id'] if isinstance(row, dict) else row[1]}\n"
                f"Link: {survey_link}\n\n"
                "Gracias por tu colaboración."
            )
            _send_smtp_email(
                smtp_host=smtp_host,
                smtp_port=smtp_port,
                smtp_user=smtp_user,
                smtp_password=smtp_password,
                from_email=from_email,
                to_emails=recipients,
                subject=subject,
                body=body,
            )

            with get_connection() as update_conn:
                update_conn.execute(
                    f"UPDATE feedback_survey_schedules SET status = {PLACEHOLDER}, sent_at = {PLACEHOLDER}, last_error = {PLACEHOLDER} WHERE id = {PLACEHOLDER}",
                    ("sent", datetime.utcnow(), None, row["id"] if isinstance(row, dict) else row[0]),
                )
                update_conn.commit()
            sent_count += 1
            _append_log(f"Sent survey for project {row['project_id'] if isinstance(row, dict) else row[1]}")
        except Exception as exc:
            with get_connection() as update_conn:
                update_conn.execute(
                    f"UPDATE feedback_survey_schedules SET status = {PLACEHOLDER}, last_error = {PLACEHOLDER} WHERE id = {PLACEHOLDER}",
                    ("failed", str(exc), row["id"] if isinstance(row, dict) else row[0]),
                )
                update_conn.commit()
            _append_log(
                f"Failed to send survey for project {row['project_id'] if isinstance(row, dict) else row[1]}: {exc}"
            )

    return sent_count
