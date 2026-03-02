"""Servicio de feedback (wrapper del processor legacy)."""

from __future__ import annotations

from ui.tabs.feedback_processor import FeedbackProcessor


class FeedbackService:
    def __init__(self, excel_manager, calculator):
        self.processor = FeedbackProcessor(excel_manager, calculator)

    def process_feedback_file(self, file_path_or_buffer):
        return self.processor.process_feedback_file(file_path_or_buffer)
