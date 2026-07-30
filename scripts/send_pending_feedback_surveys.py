"""Script para enviar las encuestas de feedback pendientes."""

from __future__ import annotations

import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from infra.feedback_survey_scheduler import send_pending_feedback_surveys


if __name__ == "__main__":
    sent_count = send_pending_feedback_surveys()
    print(f"Sent pending feedback surveys: {sent_count}")
