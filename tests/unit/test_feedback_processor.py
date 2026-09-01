import sys
import types
from unittest.mock import MagicMock

import pandas as pd

if "streamlit" not in sys.modules:
    streamlit_stub = types.ModuleType("streamlit")
    streamlit_stub.error = lambda *args, **kwargs: None
    streamlit_stub.session_state = {}
    sys.modules["streamlit"] = streamlit_stub

from ui.tabs.feedback_processor import FeedbackProcessor

PROJECT_COL_ALIAS = "ID DEL PROYECTO a evaluar"
SATISFACTION_COL = "¿Qué tan satisfecho/a estás con la nueva herramienta?"
FREQUENCY_COL = "¿Con qué frecuencia utilizas esta herramienta?"
TIME_SAVED_COL = "¿Qué porcentaje de tiempo te ahorra comparado con el proceso anterior?"
NPS_COL = "¿Qué tan probable es que recomiendes esta herramienta a un compañero?"
BENEFITS_COL = "¿Qué beneficios adicionales has notado? (opcional)"
PROBLEMS_COL = "¿Qué problemas o dificultades has enfrentado? (opcional)"


def _processor() -> FeedbackProcessor:
    return FeedbackProcessor(excel_manager=MagicMock(), calculator=MagicMock())


def test_clean_and_validate_accepts_dot_and_comma_for_percentage_values():
    processor = _processor()

    df = pd.DataFrame(
        {
            PROJECT_COL_ALIAS: ["P-001", "P-002", "P-003", "P-004"],
            SATISFACTION_COL: [8, 8, 8, 8],
            FREQUENCY_COL: ["diario", "Semanal", "mensual", "OCASIONAL"],
            TIME_SAVED_COL: ["0", "12.5", "12,5", "100"],
            NPS_COL: [9, 9, 9, 9],
            BENEFITS_COL: ["", "", "", ""],
            PROBLEMS_COL: ["", "", "", ""],
        }
    )

    cleaned = processor.clean_and_validate_data(df)

    assert cleaned is not None
    assert len(cleaned) == 4
    assert cleaned["time_reduction_percent"].tolist() == [0.0, 12.5, 12.5, 100.0]
    assert cleaned[processor.column_mapping["project_id"]].tolist() == ["P-001", "P-002", "P-003", "P-004"]
    assert cleaned[processor.column_mapping["usage_frequency"]].tolist() == [
        "Diario",
        "Semanal",
        "Mensual",
        "Ocasional",
    ]


def test_clean_and_validate_filters_invalid_ranges_and_frequency_values():
    processor = _processor()

    df = pd.DataFrame(
        {
            PROJECT_COL_ALIAS: ["OK", "BAD-SAT", "BAD-FREQ", "BAD-TIME", "BAD-NPS"],
            SATISFACTION_COL: [7, 11, 7, 7, 7],
            FREQUENCY_COL: ["Diario", "Diario", "Anual", "Diario", "Diario"],
            TIME_SAVED_COL: ["25", "25", "25", "150", "25"],
            NPS_COL: [8, 8, 8, 8, 11],
            BENEFITS_COL: ["", "", "", "", ""],
            PROBLEMS_COL: ["", "", "", "", ""],
        }
    )

    cleaned = processor.clean_and_validate_data(df)

    assert cleaned is not None
    assert len(cleaned) == 1
    assert cleaned[processor.column_mapping["project_id"]].tolist() == ["OK"]


def test_aggregate_responses_computes_nps_segments_frequency_and_unique_texts():
    processor = _processor()

    project_col = processor.column_mapping["project_id"]
    satisfaction_col = processor.column_mapping["satisfaction"]
    frequency_col = processor.column_mapping["usage_frequency"]
    benefits_col = processor.column_mapping["benefits"]
    problems_col = processor.column_mapping["problems"]
    nps_col = processor.column_mapping["nps_score"]

    df = pd.DataFrame(
        {
            project_col: ["P-100", "P-100", "P-100"],
            satisfaction_col: [9, 7, 8],
            frequency_col: ["Diario", "Diario", "Semanal"],
            "time_reduction_percent": [20.0, 30.0, 40.0],
            nps_col: [10, 8, 4],
            benefits_col: ["A", "A", "B"],
            problems_col: ["X", "", "X"],
        }
    )

    aggregated = processor.aggregate_responses_by_project(df)

    assert "P-100" in aggregated
    result = aggregated["P-100"]

    assert result["user_satisfaction_score"] == 8.0
    assert result["time_reduction_percent"] == 30.0
    assert result["survey_time_saved_percent"] == 30.0
    assert result["usage_frequency"] == "Diario"
    assert result["nps_score"] == 7.3
    assert result["nps_promoters"] == 1
    assert result["nps_passives"] == 1
    assert result["nps_detractors"] == 1
    assert result["unexpected_benefits"] == "A | B"
    assert result["challenges_faced"] == "X"
    assert result["response_count"] == 3
