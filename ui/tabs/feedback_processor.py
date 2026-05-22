# feedback_processor.py
"""
Módulo para procesar cuestionarios de feedback y actualizar tracking automáticamente
"""

import pandas as pd
import streamlit as st

from ui.tabs.shared import ExcelSharePointManager, ProjectViabilityCalculator, t


class FeedbackProcessor:
    """Procesador de cuestionarios de feedback"""

    def __init__(self, excel_manager: ExcelSharePointManager, calculator: ProjectViabilityCalculator):
        self.excel_manager = excel_manager
        self.calculator = calculator

        # Mapeo de columnas del cuestionario
        self.column_mapping = {
            "project_id": "ID DEL PROYECTO",
            "satisfaction": "Â¿Qué tan satisfecho/a estás con la nueva herramienta?",
            "time_saved_text": "Â¿Cuánto tiempo te ahorra comparado con el proceso anterior?",
            "time_saved_percent": "Â¿Qué porcentaje de tiempo te ahorra comparado con el proceso anterior?",
            "benefits": "Â¿Qué beneficios adicionales has notado? (opcional)",
            "problems": "Â¿Qué problemas o dificultades has enfrentado? (opcional)",
            "processed": "Procesado",  # Columna L para marcar como procesado
        }

    def load_feedback_excel(self, file_path_or_buffer):
        """Carga el Excel del cuestionario"""
        try:
            if isinstance(file_path_or_buffer, str):
                # Es una ruta de archivo
                df = pd.read_excel(file_path_or_buffer)
            else:
                # Es un buffer (archivo subido)
                df = pd.read_excel(file_path_or_buffer)

            return df
        except Exception as e:
            st.error(f"{t('feedback_load_error')}: {str(e)}")
            return None

    def clean_and_validate_data(self, df):
        """Limpia y valida los datos del cuestionario"""
        if df is None:
            return None

        # Verificar que existan las columnas necesarias
        required_columns = [
            self.column_mapping["project_id"],
            self.column_mapping["satisfaction"],
            self.column_mapping["time_saved_percent"],
        ]

        missing_columns = [col for col in required_columns if col not in df.columns]
        if missing_columns:
            st.error(f"{t('feedback_missing_columns')}: {missing_columns}")
            return None

        # Limpiar datos
        df_clean = df.copy()

        # Limpiar project_id
        df_clean[self.column_mapping["project_id"]] = (
            df_clean[self.column_mapping["project_id"]].astype(str).str.strip()
        )

        # Limpiar satisfacción (debe ser 1-10)
        satisfaction_col = self.column_mapping["satisfaction"]
        df_clean[satisfaction_col] = pd.to_numeric(df_clean[satisfaction_col], errors="coerce")
        df_clean = df_clean[df_clean[satisfaction_col].between(1, 10)]

        # Limpiar porcentaje de tiempo ahorrado (1-10 â†’ 0-100%)
        time_percent_col = self.column_mapping["time_saved_percent"]
        df_clean[time_percent_col] = pd.to_numeric(df_clean[time_percent_col], errors="coerce")
        df_clean = df_clean[df_clean[time_percent_col].between(1, 10)]

        # Convertir escala 1-10 a porcentaje 0-100%
        df_clean["time_reduction_percent"] = ((df_clean[time_percent_col] - 1) / 9) * 100

        # Limpiar textos
        if self.column_mapping["benefits"] in df_clean.columns:
            df_clean[self.column_mapping["benefits"]] = df_clean[self.column_mapping["benefits"]].fillna("").astype(str)

        if self.column_mapping["problems"] in df_clean.columns:
            df_clean[self.column_mapping["problems"]] = df_clean[self.column_mapping["problems"]].fillna("").astype(str)

        # Agregar columna de procesado si no existe
        if self.column_mapping["processed"] not in df_clean.columns:
            df_clean[self.column_mapping["processed"]] = ""

        return df_clean

    def get_unprocessed_responses(self, df_clean):
        """Obtiene respuestas no procesadas"""
        if df_clean is None:
            return None

        # Filtrar respuestas no procesadas (columna Procesado vací­a)
        processed_col = self.column_mapping["processed"]
        unprocessed = df_clean[
            (df_clean[processed_col].isna()) | (df_clean[processed_col] == "") | (df_clean[processed_col] == "No")
        ].copy()

        return unprocessed

    def aggregate_responses_by_project(self, df_responses):
        """Agrega respuestas por proyecto (promedio + concatenación de textos)"""
        if df_responses is None or len(df_responses) == 0:
            return {}

        project_id_col = self.column_mapping["project_id"]
        satisfaction_col = self.column_mapping["satisfaction"]
        benefits_col = self.column_mapping["benefits"]
        problems_col = self.column_mapping["problems"]

        aggregated = {}

        for project_id in df_responses[project_id_col].unique():
            project_responses = df_responses[df_responses[project_id_col] == project_id]

            # Calcular promedios
            avg_satisfaction = project_responses[satisfaction_col].mean()
            avg_time_reduction = project_responses["time_reduction_percent"].mean()

            # Concatenar textos (eliminar vací­os y duplicados)
            benefits_list = [
                str(b).strip() for b in project_responses[benefits_col] if str(b).strip() and str(b) != "nan"
            ]
            problems_list = [
                str(p).strip() for p in project_responses[problems_col] if str(p).strip() and str(p) != "nan"
            ]

            # Eliminar duplicados manteniendo orden
            benefits_unique = list(dict.fromkeys(benefits_list))
            problems_unique = list(dict.fromkeys(problems_list))

            aggregated[project_id] = {
                "user_satisfaction_score": round(avg_satisfaction, 1),
                "time_reduction_percent": round(avg_time_reduction, 1),
                "unexpected_benefits": " | ".join(benefits_unique) if benefits_unique else "",
                "challenges_faced": " | ".join(problems_unique) if problems_unique else "",
                "response_count": len(project_responses),
                "adoption_rate": 85,  # Valor por defecto, se puede ajustar
            }

        return aggregated

    def merge_with_existing_tracking(self, project_id, new_data):
        """Combina datos nuevos con tracking existente"""
        existing_trackings = self.excel_manager.get_project_tracking(project_id)

        if not existing_trackings:
            # No hay tracking existente, usar datos nuevos
            return new_data

        # Hay tracking existente, promediar con datos nuevos
        latest_tracking = existing_trackings[-1]

        # Promediar satisfacción
        existing_satisfaction = latest_tracking.get("user_satisfaction_score", 0)
        new_satisfaction = new_data["user_satisfaction_score"]
        avg_satisfaction = (existing_satisfaction + new_satisfaction) / 2

        # Para tiempo de reducción, tomar el nuevo (más actualizado)
        time_reduction = new_data["time_reduction_percent"]

        # Concatenar textos
        existing_benefits = latest_tracking.get("unexpected_benefits", "")
        new_benefits = new_data["unexpected_benefits"]
        combined_benefits = self._combine_texts(existing_benefits, new_benefits)

        existing_problems = latest_tracking.get("challenges_faced", "")
        new_problems = new_data["challenges_faced"]
        combined_problems = self._combine_texts(existing_problems, new_problems)

        # Mantener otros campos del tracking existente
        merged_data = latest_tracking.copy()
        merged_data.update(
            {
                "user_satisfaction_score": round(avg_satisfaction, 1),
                "time_reduction_percent": time_reduction,
                "unexpected_benefits": combined_benefits,
                "challenges_faced": combined_problems,
                "adoption_rate": new_data.get("adoption_rate", latest_tracking.get("adoption_rate", 85)),
                "months_tracked": latest_tracking.get("months_tracked", 3),
                "actual_time_per_task": latest_tracking.get("actual_time_per_task", 0),
                "actual_tasks_per_month": latest_tracking.get("actual_tasks_per_month", 0),
            }
        )

        return merged_data

    def _combine_texts(self, existing_text, new_text):
        """Combina textos evitando duplicación"""
        if not existing_text and not new_text:
            return ""
        if not existing_text:
            return new_text
        if not new_text:
            return existing_text

        # Dividir por separador y eliminar duplicados
        existing_parts = [part.strip() for part in existing_text.split("|") if part.strip()]
        new_parts = [part.strip() for part in new_text.split("|") if part.strip()]

        all_parts = existing_parts + new_parts
        unique_parts = list(dict.fromkeys(all_parts))  # Eliminar duplicados manteniendo orden

        return " | ".join(unique_parts)

    def update_tracking_from_feedback(self, project_id, feedback_data):
        """Actualiza o crea tracking basado en feedback"""
        try:
            # Obtener datos del proyecto
            project = self.excel_manager.get_project(project_id)
            if not project:
                return False, f"Proyecto {project_id} no encontrado"

            # Combinar con tracking existente si existe
            merged_data = self.merge_with_existing_tracking(project_id, feedback_data)

            # Calcular tiempo real basado en porcentaje de reducción
            original_time = project["current_time_per_task"]
            time_reduction_percent = merged_data["time_reduction_percent"]
            actual_time_per_task = original_time * (1 - time_reduction_percent / 100)

            # Preparar datos completos para tracking
            tracking_data = {
                "months_tracked": merged_data.get("months_tracked", 3),
                "actual_time_per_task": actual_time_per_task,
                "actual_tasks_per_month": merged_data.get("actual_tasks_per_month", project["tasks_per_month"]),
                "adoption_rate": merged_data["adoption_rate"],
                "user_satisfaction_score": merged_data["user_satisfaction_score"],
                "unexpected_benefits": merged_data["unexpected_benefits"],
                "challenges_faced": merged_data["challenges_faced"],
                "lessons_learned": merged_data.get("lessons_learned", ""),
            }

            # Crear o actualizar tracking
            tracking_id, results = self.calculator.add_tracking(project_id, tracking_data)

            return True, f"Tracking actualizado: {tracking_id}"

        except Exception as e:
            return False, f"Error actualizando tracking: {str(e)}"

    def mark_responses_as_processed(self, df_original, df_responses, file_path=None):
        """Marca respuestas como procesadas en el Excel original"""
        try:
            df_updated = df_original.copy()

            # Marcar como procesadas
            project_id_col = self.column_mapping["project_id"]
            processed_col = self.column_mapping["processed"]

            # Asegurar que existe la columna Procesado
            if processed_col not in df_updated.columns:
                df_updated[processed_col] = ""

            for _, response in df_responses.iterrows():
                project_id = response[project_id_col]
                # Marcar todas las respuestas de este proyecto como procesadas
                mask = df_updated[project_id_col] == project_id
                df_updated.loc[mask, processed_col] = "Sí­"

            # Guardar archivo actualizado si se proporciona ruta
            if file_path:
                df_updated.to_excel(file_path, index=False)

            return df_updated

        except Exception as e:
            st.error(f"{t('feedback_mark_processed_error')}: {str(e)}")
            return df_original

    def process_feedback_file(self, uploaded_file_or_path):
        """Procesa archivo completo de feedback"""
        results = {
            "success": True,
            "processed_projects": [],
            "errors": [],
            "total_responses": 0,
            "processed_responses": 0,
        }

        try:
            # Cargar datos
            df_original = self.load_feedback_excel(uploaded_file_or_path)
            if df_original is None:
                results["success"] = False
                results["errors"].append("No se pudo cargar el archivo")
                return results

            results["total_responses"] = len(df_original)

            # Limpiar y validar
            df_clean = self.clean_and_validate_data(df_original)
            if df_clean is None:
                results["success"] = False
                results["errors"].append("Error en validación de datos")
                return results

            # Obtener respuestas no procesadas
            df_unprocessed = self.get_unprocessed_responses(df_clean)
            if df_unprocessed is None or len(df_unprocessed) == 0:
                results["errors"].append("No hay respuestas nuevas para procesar")
                return results

            results["processed_responses"] = len(df_unprocessed)

            # Agregar por proyecto
            aggregated_data = self.aggregate_responses_by_project(df_unprocessed)

            # Procesar cada proyecto
            for project_id, feedback_data in aggregated_data.items():
                success, message = self.update_tracking_from_feedback(project_id, feedback_data)

                if success:
                    results["processed_projects"].append(
                        {
                            "project_id": project_id,
                            "responses": feedback_data["response_count"],
                            "satisfaction": feedback_data["user_satisfaction_score"],
                            "time_reduction": feedback_data["time_reduction_percent"],
                        }
                    )
                else:
                    results["errors"].append(f"Proyecto {project_id}: {message}")

            # Marcar como procesadas
            if isinstance(uploaded_file_or_path, str):
                self.mark_responses_as_processed(df_original, df_unprocessed, uploaded_file_or_path)

        except Exception as e:
            results["success"] = False
            results["errors"].append(f"Error general: {str(e)}")

        return results


def render_feedback_processor():
    """Renderiza la interfaz del procesador de feedback"""
    st.header(t("feedback_processor_header"))

    st.info(t("feedback_processor_how_it_works"))

    # Inicializar procesador
    if "feedback_processor" not in st.session_state:
        st.session_state.feedback_processor = FeedbackProcessor(
            st.session_state.excel_manager, st.session_state.calculator
        )

    processor = st.session_state.feedback_processor

    # Tabs para diferentes opciones
    tab1, tab2, tab3 = st.tabs([t("feedback_tab_upload"), t("feedback_tab_preview"), t("feedback_tab_history")])

    with tab1:
        st.subheader(t("feedback_upload_file_subheader"))

        uploaded_file = st.file_uploader(
            t("feedback_select_excel_label"), type=["xlsx", "xls"], help=t("feedback_select_excel_help")
        )

        if uploaded_file is not None:
            # Preview de datos
            with st.expander(t("feedback_preview_data_expander")):
                df_preview = processor.load_feedback_excel(uploaded_file)
                if df_preview is not None:
                    st.write(f"**{t('feedback_total_responses')}** {len(df_preview)}")
                    st.dataframe(df_preview.head(), use_container_width=True)

            # Botón de procesamiento
            if st.button(t("feedback_process_btn"), type="primary"):
                with st.spinner(t("feedback_processing_spinner")):
                    results = processor.process_feedback_file(uploaded_file)

                # Mostrar resultados
                if results["success"] and results["processed_projects"]:
                    st.success(t("feedback_processing_success"))

                    col1, col2, col3 = st.columns(3)
                    with col1:
                        st.metric(t("feedback_total_responses_metric"), results["total_responses"])
                    with col2:
                        st.metric(t("feedback_processed_responses_metric"), results["processed_responses"])
                    with col3:
                        st.metric(t("feedback_updated_projects_metric"), len(results["processed_projects"]))

                    # Detalles por proyecto
                    st.subheader(t("feedback_updated_projects_subheader"))
                    for project in results["processed_projects"]:
                        with st.expander(f"{t('project_label')} {project['project_id']}"):
                            col_p1, col_p2, col_p3 = st.columns(3)
                            with col_p1:
                                st.metric(t("feedback_responses_metric"), project["responses"])
                            with col_p2:
                                st.metric(t("feedback_satisfaction_metric"), f"{project['satisfaction']}/10")
                            with col_p3:
                                st.metric(t("feedback_time_saved_metric"), f"{project['time_reduction']:.1f}%")

                # Mostrar errores si los hay
                if results["errors"]:
                    st.warning(t("feedback_warnings_found"))
                    for error in results["errors"]:
                        st.write(f"â€¢ {error}")

    with tab2:
        st.subheader(t("feedback_preview_questionnaire_subheader"))

        st.markdown(t("feedback_expected_excel_structure_markdown"))

        # Mostrar mapeo de conversiones
        st.subheader(t("feedback_auto_conversions_subheader"))

        col_conv1, col_conv2 = st.columns(2)

        with col_conv1:
            st.markdown(t("feedback_satisfaction_conversion_markdown"))
            satisfaction_example = pd.DataFrame({"Cuestionario": [1, 5, 8, 10], "Tracking": [1, 5, 8, 10]})
            st.dataframe(satisfaction_example, hide_index=True)

        with col_conv2:
            st.markdown(t("feedback_time_saved_conversion_markdown"))
            time_example = pd.DataFrame({"Cuestionario (1-10)": [1, 3, 7, 10], "Tracking (%)": [0, 22.2, 66.7, 100]})
            st.dataframe(time_example, hide_index=True)

    with tab3:
        st.subheader(t("feedback_processing_history_subheader"))

        # Mostrar proyectos con tracking
        projects_with_tracking = []
        for project in st.session_state.excel_manager.get_all_projects():
            trackings = st.session_state.excel_manager.get_project_tracking(project["id"])
            if trackings:
                latest = trackings[-1]
                projects_with_tracking.append(
                    {
                        "ID": project["id"],
                        "Nombre": project["name"],
                        "Satisfacción": f"{latest.get('user_satisfaction_score', 0)}/10",
                        "Adopción": f"{latest.get('adoption_rate', 0)}%",
                        "Última Actualización": (
                            latest.get("tracking_date", "")[:10] if latest.get("tracking_date") else "N/A"
                        ),
                    }
                )

        if projects_with_tracking:
            df_tracking_history = pd.DataFrame(projects_with_tracking)
            st.dataframe(df_tracking_history, use_container_width=True, hide_index=True)
        else:
            st.info(t("feedback_no_projects_with_tracking"))
