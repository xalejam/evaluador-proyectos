"""Etiquetas i18n para catalogos UI manteniendo codigos internos."""

from __future__ import annotations

import streamlit as st

STATUS_LABELS = {
    "evaluated": {"es": "Evaluado", "pt": "Avaliado", "en": "Evaluated"},
    "backlog": {
        "es": "Backlog (Pendiente por priorizar)",
        "pt": "Backlog (Pendente de priorizacao)",
        "en": "Backlog (Pending prioritization)",
    },
    "on_hold": {
        "es": "En espera (Sin capacidad disponible)",
        "pt": "Em espera (Sem capacidade disponivel)",
        "en": "On hold (No available capacity)",
    },
    "rejected": {"es": "Rechazado", "pt": "Rejeitado", "en": "Rejected"},
    "handed_off": {
        "es": "Transferido a otro equipo",
        "pt": "Transferido para outro time",
        "en": "Handed off to another team",
    },
    "approved": {"es": "Aprobado", "pt": "Aprovado", "en": "Approved"},
    "in_agenda": {"es": "En agenda", "pt": "Na agenda", "en": "In agenda"},
    "executing": {"es": "En ejecucion", "pt": "Em execucao", "en": "Executing"},
    "implemented": {"es": "Implementado", "pt": "Implementado", "en": "Implemented"},
}


STATUS_HELP = {
    "es": (
        "Define el estado en que se guardara esta evaluacion.\n"
        "- Evaluado: Solo registra la evaluacion, sin compromiso de ejecucion.\n"
        "- Backlog: Idea valida pendiente de priorizacion.\n"
        "- En espera: Proyecto viable pero sin capacidad disponible.\n"
        "- Rechazado: No se ejecutara.\n"
        "- Transferido: Se asigna a otro equipo."
    ),
    "pt": (
        "Define o estado em que esta avaliacao sera salva.\n"
        "- Avaliado: Apenas registra a avaliacao, sem compromisso de execucao.\n"
        "- Backlog: Ideia valida pendente de priorizacao.\n"
        "- Em espera: Projeto viavel, mas sem capacidade disponivel.\n"
        "- Rejeitado: Nao sera executado.\n"
        "- Transferido: Encaminhado para outro time."
    ),
    "en": (
        "Defines the status used when saving this evaluation.\n"
        "- Evaluated: Stores assessment only, without execution commitment.\n"
        "- Backlog: Valid idea pending prioritization.\n"
        "- On hold: Viable project without available capacity.\n"
        "- Rejected: Will not be executed.\n"
        "- Handed off: Assigned to another team."
    ),
}

NOTE_TYPE_LABELS = {
    "general": {"es": "General", "pt": "Geral", "en": "General"},
    "proximo_paso": {"es": "Próximo paso", "pt": "Próximo passo", "en": "Next step"},
    "bloqueador": {"es": "Bloqueador", "pt": "Bloqueador", "en": "Blocker"},
    "riesgo": {"es": "Riesgo", "pt": "Risco", "en": "Risk"},
}


def get_lang() -> str:
    lang = str(st.session_state.get("language", "es")).lower()
    return lang if lang in ("es", "pt", "en") else "es"


def label_status(status_code: str, lang: str | None = None) -> str:
    current_lang = lang or get_lang()
    labels = STATUS_LABELS.get(status_code, {})
    return labels.get(current_lang, labels.get("es", status_code))


def help_statuses(lang: str | None = None) -> str:
    current_lang = lang or get_lang()
    return STATUS_HELP.get(current_lang, STATUS_HELP["es"])


def label_note_type(note_type_code: str, lang: str | None = None) -> str:
    current_lang = lang or get_lang()
    labels = NOTE_TYPE_LABELS.get(note_type_code, {})
    return labels.get(current_lang, labels.get("es", note_type_code))
