# shared.py
"""
Módulo compartido con traducciones, clases principales y funciones utilitarias
"""

import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from datetime import datetime, date
import io
import uuid
import os
import sqlite3
import json
import re

# =============================================================================
# TRADUCCIONES / TRANSLATIONS — re-exported from ui.i18n (source of truth)
# =============================================================================
from ui.i18n import TRANSLATIONS, t, get_language  # noqa: F401, E402

_TRANSLATIONS_LEGACY = {
    "es": {
        # Header y navegación
        "page_title": "Evaluador de Viabilidad - Proyectos IA/Automatización",
        "main_title": "Evaluador de Viabilidad de Proyectos",
        "main_subtitle": "Analiza la viabilidad técnica de tus proyectos de IA y automatización",
        "language_label": "🌍 Idioma",
        "planning_tab": "📋 Planificación",
        "viability_tab": "Viabilidad",
        "operational_log_tab": "Bitácora",
        "impact_kpis_tab": "Impacto & KPIs",
        "tracking_tab": "📊 Seguimiento Post-Implementación",
        "dashboard_tab": "📈 Dashboard",
        "use_case_matrix_tab": "Matriz Impacto-Esfuerzo",
        "feedback_tab": "Feedback",
        "sql_tab": "SQL",
        "platform_title": "Plataforma Integral de Gestión de Proyectos de Automatización",
        "platform_subtitle": "Planifica, evalúa, da seguimiento y analiza proyectos de IA y automatización en un solo lugar.",
        # Gestión de archivos
        "file_management": "📁 Gestión de Archivos",
        "upload_excel": "📤 Cargar Excel existente",
        "upload_help": "Sube un archivo Excel con datos previos",
        "load_data_btn": "🔄 Cargar datos",
        "data_loaded": "✅ Datos cargados exitosamente",
        "generate_excel_btn": "💾 Generar Excel para SharePoint",
        "download_excel_btn": "📥 Descargar Excel",
        "sharepoint_steps": """📋 **Pasos para SharePoint:**
1. Descarga el archivo Excel
2. Súbelo a tu sitio SharePoint  
3. Comparte el link con el equipo
4. Todos pueden descargar, editar y volver a subir""",
        "save_local_btn": "💿 Guardar localmente",
        "saved_local": "✅ Guardado en project_viability.xlsx",
        # Búsqueda de proyectos
        "search_projects": "🔍 Buscar Proyectos",
        "search_placeholder": 'ej: a1b2c3d4 o "lead scoring"',
        "projects_found": "proyecto(s) encontrado(s)",
        "no_projects_found": "⚠️ No se encontraron proyectos",
        "edit_btn": "📝 Editar",
        # Estadísticas sidebar
        "statistics": "📊 Estadísticas",
        "total_projects": "Proyectos",
        "total_trackings": "Seguimientos",
        "high_priority": "Alta Prioridad",
        "implemented": "Implementados",
        "executing": "En ejecución",
        # Formulario de proyecto
        "project_info": "Información del Proyecto",
        "project_name": "Nombre del Proyecto",
        "project_name_placeholder": "ej: Automatización de lead scoring",
        "project_description": "Descripción",
        "project_description_placeholder": "Breve descripción del proyecto...",
        "current_situation": "Situación Actual",
        "time_per_task": "Tiempo por tarea (hrs)",
        "tasks_per_month": "Tareas por mes",
        "staff_count": "Personal involucrado",
        "salary_scale": "Scale Salarial",
        "dev_salary_scale": "Scale del Desarrollador",
        "salary_custom": "Personalizado",
        "cost_per_hour": "Costo por hora (USD)",
        # Scale levels (sin horas visibles)
        "scale_levels": {
            "Scale 40": "Scale 40",
            "Scale 50": "Scale 50",
            "Scale 60": "Scale 60",
            "Scale 70": "Scale 70",
            "Scale 80": "Scale 80",
            "Scale 90": "Scale 90",
            "Personalizado": "Personalizado",
        },
        # Mejoras esperadas
        "expected_improvements": "Mejoras Esperadas",
        "time_reduction": "Reducción de tiempo (%)",
        # Costos del proyecto
        "project_costs": "Costos del Proyecto",
        "development_hours": "Horas de desarrollo",
        "monthly_maintenance": "Mantenimiento mensual (USD)",
        # Factores de riesgo (selectores simples)
        "risk_factors": "Factores de Riesgo",
        "implementation_complexity": "Complejidad de implementación (1-5)",
        "technical_risk": "Nivel de riesgo técnico (1-5)",
        # Opciones simples para complejidad
        "complexity_options": {
            1: "1 - Muy simple",
            2: "2 - Simple",
            3: "3 - Moderada",
            4: "4 - Compleja",
            5: "5 - Muy compleja",
        },
        # Opciones simples para riesgo
        "risk_options": {1: "1 - Muy bajo", 2: "2 - Bajo", 3: "3 - Medio", 4: "4 - Alto", 5: "5 - Muy alto"},
        # Botones principales
        "create_project_btn": "💾 Crear Proyecto",
        "update_project_btn": "🔄 Actualizar Proyecto",
        "new_project_btn": "➕ Nuevo Proyecto",
        "search_edit_btn": "🔍 Buscar/Editar",
        "cancel_btn": "❌ Cancelar",
        # Resultados y scoring
        "viability_score": "Score de Viabilidad",
        "priority": "Prioridad",
        "financial_analysis": "Análisis Financiero",
        "monthly_savings": "Ahorro Mensual",
        "annual_savings": "Ahorro Anual",
        "initial_investment": "Inversión Inicial",
        "payback_period": "Recuperación",
        "efficiency_improvements": "Mejoras de Eficiencia",
        "hours_saved_month": "Horas ahorradas por mes",
        "time_reduction_achieved": "Reducción de tiempo",
        "first_year_roi": "ROI primer año",
        # Estados y prioridades
        "priority_high": "Alta",
        "priority_medium_high": "Media-Alta",
        "priority_medium": "Media",
        "priority_low": "Baja",
        # Recomendaciones del nuevo sistema
        "recommendation_80_100": "Proyecto altamente factible. Excelente impacto y baja complejidad.",
        "recommendation_60_79": "Proyecto factible. Buen impacto con riesgo controlado.",
        "recommendation_40_59": "Proyecto marginal. Evaluar simplificación antes de proceder.",
        "recommendation_0_39": "Proyecto no recomendado. Alto riesgo o complejidad excesiva.",
        # Mensajes de éxito/error
        "project_created": "✅ Proyecto creado",
        "project_updated": "✅ Proyecto actualizado",
        "error_occurred": "❌ Error",
        "name_required": "❌ Nombre del proyecto es obligatorio",
        "project_in_memory": "✅ Proyecto en Memoria",
        "created_date": "Creado",
        "status": "Estado",
        "create_search_prompt": "👆 Crear o buscar un proyecto para ver los resultados aquí",
        "project_not_found": "❌ Proyecto no encontrado",
        "project_label": "Proyecto",
        "project_id_pending": "Se generará al guardar",
        "na": "N/D",
        "current_score": "Score actual",
        "loop_label": "Loop",
        "open_loop_btn": "Abrir Loop",
        "no_link": "Sin link",
        "evaluation_form": "Formulario de evaluación",
        "owner_help": "Se usa para generar ID tipo PAIS-OWNER-NNNN",
        "owner_label": "Owner",
        "country_iso2": "Country (ISO2)",
        "financial_average_rate_caption": "💡 Cálculos financieros con hora promedio:",
        "optional_details": "Detalles opcionales",
        "scale_reference_help": "No afecta cálculos de ROI.",
        "developer_team_label": "Equipo de desarrollo",
        "loop_url_label": "Loop URL",
        "loop_optional_viability_note": "Opcional en Viabilidad. Debe quedar completo en Bitácora (primera entrada).",
        "save_evaluation_status_label": "Estado al guardar evaluación",
        "action_owner_label": "Responsable de la acción",
        "evaluate_btn": "🧮 Evaluar",
        "save_evaluation_btn": "💾 Guardar evaluación",
        "approve_to_agenda_btn": "✅ Aprobar (pasar a agenda)",
        "owner_required": "Owner es obligatorio para generar el ID del proyecto.",
        "evaluation_calculated_not_saved": "Evaluación calculada. No se guardó en base de datos.",
        "loop_required_for_approval": "Para aprobar debes registrar el link de Loop.",
        "project_approved_sent_to_agenda": "Proyecto aprobado y enviado a agenda.",
        "folder_provisioned_ok": "📁 Carpeta creada: {path} (color: {color})",
        "folder_provisioned_warning": "⚠️ Proyecto aprobado pero no se pudo crear la carpeta: {error}",
        "evaluation_saved_msg": "Evaluación guardada.",
        "evaluate_to_view_results_info": "Evalúa un proyecto para ver resultados. Evaluar no persiste; Guardar/Aprobar sí.",
        "temporary_results_warning": "Resultados temporales: aún no persistidos.",
        "persisted_results_success": "Resultados persistidos.",
        "sql_tab_header": "🗄️ Consultas SQL",
        "sql_tab_caption": "Ejecuta consultas SELECT sobre la base SQLite local.",
        "sql_available_tables_markdown": "Tablas disponibles:\n- `projects`\n- `tracking`",
        "sql_query_input_label": "Consulta SQL (solo lectura)",
        "sql_run_select_btn": "▶ Ejecutar SELECT",
        "sql_clear_btn": "🧹 Limpiar",
        "sql_download_csv_btn": "📥 Descargar resultado (CSV)",
        "sql_error_empty": "La consulta está vacía.",
        "sql_error_single_statement": "Solo se permite una sentencia SQL.",
        "sql_error_readonly": "Solo se permiten consultas SELECT (incluyendo WITH ... SELECT).",
        "sql_error_forbidden_keyword": "Consulta bloqueada por palabra reservada no permitida:",
        "sql_error_running_query": "Error ejecutando consulta",
        "sql_query_ok_rows": "Consulta ejecutada. Filas:",
        "ucm_header": "Matriz Impacto-Esfuerzo",
        "ucm_schema_init_error": "No se pudo inicializar esquema de matriz",
        "ucm_load_portfolio_error": "No se pudo cargar portafolio",
        "ucm_no_saved_projects": "No hay proyectos guardados (Guardar evaluación / Aprobar).",
        "ucm_no_scores_filtered": "No hay scores de Impact/Effort para los filtros seleccionados.",
        "ucm_year_filter": "Año",
        "ucm_team_filter": "Equipo",
        "ucm_no_team": "Sin equipo",
        "ucm_status_filter": "Estado",
        "ucm_search_filter": "Búsqueda (nombre, owner, project_id)",
        "ucm_detail_title": "Detalle del proyecto",
        "ucm_no_detail_results": "Sin resultados para mostrar detalle.",
        "ucm_select_project": "Selecciona proyecto",
        "ucm_open_viability_btn": "Abrir en Viabilidad",
        "ucm_open_viability_hint": "Proyecto cargado en session_state. Ve a la pestaña 'Viabilidad'.",
        "ucm_change_status": "Cambiar estado",
        "ucm_save_status_btn": "Guardar estado",
        "ucm_status_updated": "Estado actualizado a",
        "ucm_status_update_error": "No se pudo actualizar estado",
        "ucm_filtered_dataset": "Dataset filtrado",
        "download_csv": "Descargar CSV",
        "download_json": "Descargar JSON",
        "ops_projects_table_missing": "No existe la tabla projects. Crea proyectos primero en Viabilidad.",
        "ops_demo_loaded": "Datos demo cargados.",
        "ops_demo_load_error": "No se pudo cargar demo",
        "ops_last_notes_title": "Últimas notas del proyecto",
        "ops_no_note": "Sin nota",
        "ops_tags_label": "Tags",
        "ops_quick_capture": "Captura rápida",
        "ops_included_statuses": "Estados incluidos",
        "ops_no_eligible_projects": "No hay proyectos elegibles para captura rápida.",
        "ops_no_notes": "Sin notas",
        "ops_last_update": "Última actualización",
        "ops_progress_last_value": "Último avance",
        "ops_progress_last_date": "Fecha último avance",
        "ops_progress_no_data": "Sin datos de avance",
        "ops_progress_capture_enable": "Registrar % de avance en esta actualización",
        "ops_progress_percent_label": "% avance del proyecto",
        "ops_estimated_end_date_label": "Fecha estimada de cierre (opcional)",
        "ops_progress_suggested": "Progreso sugerido basado en días transcurridos",
        "ops_progress_trend": "Tendencia de avance",
        "ops_progress_drop_warning": "Progreso bajó sin justificación visible:",
        "ops_progress_overview_title": "Avance por proyecto",
        "ops_first_entry_loop_required": "Primera entrada del proyecto: el link de Loop es obligatorio antes de guardar la actualización.",
        "ops_loop_missing_warning": "Este proyecto aún no tiene link de Loop. Debes configurarlo para continuar registrando entradas.",
        "ops_loop_doc_link": "Link de documentación (Loop)",
        "ops_save_link_btn": "Guardar link",
        "ops_link_updated": "Link actualizado.",
        "ops_link_save_error": "No se pudo guardar link",
        "ops_note_title_optional": "Título de la actualización (opcional)",
        "ops_recent_tags": "Tags recientes",
        "ops_extra_tags_csv": "Tags extra (CSV)",
        "ops_extra_tags_placeholder": "comercial,etl,pendiente",
        "ops_author": "Autor",
        "ops_save_update_btn": "Guardar actualización",
        "ops_author_required": "El autor es obligatorio.",
        "ops_loop_required_to_save": "Debes ingresar el link de Loop para guardar la actualización.",
        "ops_no_content_to_save": "No hay contenido para guardar. Completa al menos una sección.",
        "ops_update_saved": "Actualización guardada. Grupo:",
        "ops_notes_inserted": "Notas insertadas",
        "ops_save_update_error": "Error al guardar actualización",
        "ops_executive_summary": "Resumen ejecutivo",
        "ops_states": "Estados",
        "ops_search": "Búsqueda",
        "ops_days_without_update": "Días sin update (>=)",
        "ops_summary_build_error": "No se pudo construir el resumen",
        "ops_no_results_filters": "No hay resultados para los filtros seleccionados.",
        "ops_update_title": "Actualización",
        "ops_timeline_history": "Timeline / Histórico",
        "ops_project_timeline_select": "Proyecto (timeline por proyecto)",
        "ops_search_text": "Buscar texto",
        "ops_filter_tag": "Filtrar tag",
        "ops_type": "Tipo",
        "ops_all": "Todos",
        "ops_limit": "Límite",
        "ops_from": "Desde",
        "ops_to": "Hasta",
        "ops_project_view": "Vista por proyecto",
        "ops_no_project_notes_filtered": "No hay notas para el proyecto con los filtros seleccionados.",
        "ops_project_timeline_label": "timeline proyecto",
        "ops_global_view": "Vista global",
        "ops_no_global_notes_filtered": "No hay notas globales con los filtros seleccionados.",
        "ops_global_timeline_label": "timeline global",
        "ops_tab_caption": "Notas inmutables por proyecto. V2 con captura rápida, resumen ejecutivo y timeline.",
        "ops_schema_init_error": "No se pudo inicializar esquema",
        "ops_load_demo": "Cargar datos demo",
        "ops_error_quick_capture": "Error en Captura rápida",
        "ops_error_executive_summary": "Error en Resumen ejecutivo",
        "ops_error_timeline": "Error en Timeline / Histórico",
        "ops_note_help_general": "Contexto, decisión y resultado.",
        "ops_note_help_next_step": "Acción concreta + responsable + fecha compromiso.",
        "ops_note_help_blocker": "Impedimento real + impacto + quien destraba.",
        "ops_note_help_risk": "Riesgo potencial + probabilidad + mitigación.",
        "ops_note_example_general": 'Ejemplo: "Se validó alcance con Comercial y TI".',
        "ops_note_example_next_step": 'Ejemplo: "Enviar brief a TI - Ana - 12/03".',
        "ops_note_example_blocker": 'Ejemplo: "Falta acceso API; lo destraba soporte TI".',
        "ops_note_example_risk": 'Ejemplo: "Riesgo de cambio de owner; mitigar con handoff documentado".',
        "ops_capture_help_info": 'Guía rápida:\n- General: contexto y decisión. Ejemplo: "Se validó alcance con Comercial".\n- Próximo paso: acción + responsable + fecha. Ejemplo: "Enviar brief a TI - Ana - 12/03".\n- Bloqueador: qué detiene y quién destraba. Ejemplo: "Falta acceso API - soporte TI".\n- Riesgo: posible problema y mitigación. Ejemplo: "Cambio de owner; documentar handoff".',
        "project_links_section": "Accesos del proyecto",
        "loop_link": "Loop link",
        "repo_link": "Repo link",
        "artifacts_link": "Artefactos link",
        "open_repo_btn": "Abrir Repo",
        "open_artifacts_btn": "Abrir Artefactos",
        "configure_links": "Configurar enlaces",
        "save_links": "Guardar accesos",
        "ops_links_updated": "Accesos actualizados.",
        "ops_status_changed_to": "Estado actualizado a",
        "repo_help": "Link al repo en Azure DevOps.",
        "artifacts_help": "Link a SharePoint/carpeta/Power BI/otro.",
        "artifacts_type": "Tipo de artefacto",
        "tech_stack": "Stack tecnológico",
        "artifacts_type_azure_devops": "Azure DevOps",
        "artifacts_type_sharepoint": "SharePoint",
        "artifacts_type_powerbi": "Power BI",
        "artifacts_type_excel_vba": "Excel/VBA",
        "artifacts_type_folder": "Carpeta",
        "artifacts_type_agent": "Agente IA",
        "artifacts_type_other": "Otro",
        "tech_stack_python": "Python",
        "tech_stack_vba": "VBA",
        "tech_stack_powerbi": "Power BI",
        "tech_stack_agent": "Agente IA",
        "tech_stack_other": "Otro",
        "tracking_auto_data_info": "🤖 **Datos actualizados automáticamente desde encuesta.** Puedes modificar manualmente si es necesario.",
        "tracking_manual_or_wait_info": "✋ **Completar manualmente** o esperar datos de encuesta automática.",
        "tracking_update_btn": "🔄 Actualizar Tracking",
        "tracking_updated_manual": "🔄 Tracking actualizado manualmente",
        "tracking_auto_source": "🤖 Datos de encuesta automática",
        "tracking_manual_source": "✋ Datos ingresados manualmente",
        "tracking_qualitative_analysis": "📝 Análisis Cualitativo",
        "tracking_unexpected_benefits_expander": "✅ Beneficios Inesperados",
        "tracking_challenges_expander": "⚠️ Desafíos Enfrentados",
        "tracking_lessons_expander": "💡 Lecciones Aprendidas",
        "tracking_recommendations": "🎯 Recomendaciones",
        "tracking_reco_replicate": "✅ Replicar este enfoque en proyectos similares",
        "tracking_reco_review_method": "⚠️ Revisar metodología de estimación para futuros proyectos",
        "tracking_reco_change_training": "👥 Mejorar estrategias de cambio organizacional y entrenamiento",
        "tracking_reco_involve_users": "🎯 Involucrar más a usuarios finales en el diseño de soluciones",
        "tracking_reco_expand_scope": "🏆 Considerar expandir el alcance del proyecto",
        "tracking_project_on_track": "🎉 El proyecto está funcionando según lo esperado",
        "tracking_no_tracking_for_project": "📝 No hay seguimientos para este proyecto",
        "tracking_project_info_title": "📋 Información del Proyecto",
        "tracking_auto_when_feedback": "🤖 El tracking se completará automáticamente cuando haya respuestas de encuesta",
        "tracking_fill_form_hint": "👆 Completa el formulario de la izquierda para comenzar el seguimiento",
        "tracking_feedback_file_not_found": "No se encontró el archivo",
        "tracking_feedback_missing_columns": "El archivo no tiene las columnas requeridas",
        "tracking_feedback_read_error": "Error leyendo archivo",
        "tracking_feedback_processed_ok": "✅ Respuestas nuevas procesadas:",
        "tracking_feedback_no_new": "📝 Archivo encontrado, no hay respuestas nuevas para procesar:",
        "tracking_unknown_error": "Error desconocido",
        "tracking_feedback_process_error": "❌ Error procesando",
        "tracking_auto_process_error": "❌ Error en procesamiento automático",
        "tracking_source_no_tracking": "📝 Sin seguimiento",
        "tracking_source_auto_survey": "🤖 Automático (encuesta)",
        "tracking_source_manual": "✋ Manual",
        "tracking_source_no_data": "📝 Sin datos",
        "tracking_spinner_search_feedback": "🔍 Buscando actualizaciones de encuestas...",
        "tracking_updated_projects_expander": "📊 Ver proyecto(s) actualizado(s)",
        "tracking_satisfaction_label": "Satisfacción",
        "tracking_time_saved_label": "Tiempo ahorrado",
        "tracking_status_prefix": "📊 **Estado del tracking**",
        "tracking_efficiency_label": "Eficiencia",
        "tracking_no_implemented_warning": "No hay proyectos implementados para seguimiento post-implementación.",
        "dashboard_scores_distribution": "📊 Distribución de Scores",
        "dashboard_priority_distribution": "🎯 Distribución por Prioridad",
        "dashboard_viability_vs_roi": "📈 Score de Viabilidad vs ROI",
        "dashboard_factor_analysis": "🔍 Análisis de Factores",
        "dashboard_tracking_metrics": "📊 Métricas de Seguimiento",
        "dashboard_scatter_caption": "💡 Los puntos por encima de la línea roja indican proyectos que superaron las expectativas iniciales",
        "dashboard_portfolio_insights": "💡 Insights del Portfolio",
        "dashboard_add_more_for_insights": "📈 Continúa añadiendo proyectos y seguimientos para obtener insights personalizados",
        "dashboard_export_excel_btn": "📥 Exportar Dashboard como Excel",
        "dashboard_scores_distribution_title": "Distribución de Scores de Viabilidad",
        "dashboard_num_projects": "Número de Proyectos",
        "dashboard_projects_by_priority": "Proyectos por Prioridad",
        "dashboard_viability_roi_relation": "Relación entre Score de Viabilidad y ROI",
        "dashboard_complexity_distribution_title": "Distribución por Complejidad",
        "dashboard_complexity_level": "Nivel de Complejidad (1-5)",
        "dashboard_technical_risk_distribution_title": "Distribución por Riesgo Técnico",
        "dashboard_risk_level": "Nivel de Riesgo (1-5)",
        "dashboard_avg_performance": "Performance Promedio",
        "dashboard_avg_efficiency": "Eficiencia Promedio",
        "dashboard_avg_adoption": "Adopción Promedio",
        "dashboard_avg_satisfaction": "Satisfacción Promedio",
        "dashboard_initial_vs_real_performance": "Score Inicial vs Performance Real",
        "dashboard_initial_viability_score": "Score de Viabilidad Inicial",
        "dashboard_real_performance_percent": "Performance Real (%)",
        "dashboard_insight_portfolio_solid": "🎯 **Portfolio sólido**: Más del 50% de los proyectos tienen alta viabilidad",
        "dashboard_insight_high_complexity": "⚠️ **Alta complejidad**: Considerar simplificar algunos proyectos para mejor ejecución",
        "dashboard_insight_implementation_success": "✅ **Implementación exitosa**: La mayoría de proyectos ejecutados superan expectativas",
        "feedback_processor_header": "📊 Procesador de Cuestionarios de Feedback",
        "feedback_processor_how_it_works": "**¿Cómo funciona?**\n\n1. 📤 **Sube el Excel** del cuestionario con las respuestas\n2. 🔄 **Procesamiento automático:** Convierte respuestas en datos de tracking\n3. 📊 **Actualización:** Los proyectos se actualizan con datos reales\n4. ✅ **Marcado:** Las respuestas procesadas se marcan para evitar duplicados",
        "feedback_tab_upload": "📤 Subir Cuestionario",
        "feedback_tab_preview": "🔍 Preview Datos",
        "feedback_tab_history": "📋 Historial",
        "feedback_upload_file_subheader": "📤 Subir Archivo de Cuestionario",
        "feedback_select_excel_label": "Selecciona el Excel del cuestionario",
        "feedback_select_excel_help": "Archivo con las respuestas del cuestionario de feedback",
        "feedback_preview_data_expander": "👀 Preview de Datos",
        "feedback_total_responses": "Total de respuestas:",
        "feedback_process_btn": "🚀 Procesar Cuestionario",
        "feedback_processing_spinner": "Procesando respuestas...",
        "feedback_processing_success": "✅ ¡Procesamiento exitoso!",
        "feedback_total_responses_metric": "Respuestas Totales",
        "feedback_processed_responses_metric": "Respuestas Procesadas",
        "feedback_updated_projects_metric": "Proyectos Actualizados",
        "feedback_updated_projects_subheader": "📊 Proyectos Actualizados",
        "feedback_responses_metric": "Respuestas",
        "feedback_satisfaction_metric": "Satisfacción",
        "feedback_time_saved_metric": "Tiempo Ahorrado",
        "feedback_warnings_found": "⚠️ Algunos problemas encontrados:",
        "feedback_preview_questionnaire_subheader": "🔍 Preview de Datos del Cuestionario",
        "feedback_expected_excel_structure_markdown": "**Estructura esperada del Excel:**\n\n| Columna | Descripción | Formato |\n|---------|-------------|---------|\n| ID DEL PROYECTO | Identificador del proyecto | Texto (ej: a1b2c3d4) |\n| ¿Qué tan satisfecho/a estás...? | Satisfacción del usuario | Número 1-10 |\n| ¿Qué porcentaje de tiempo...? | Tiempo ahorrado | Número 1-10 (se convierte a %) |\n| ¿Qué beneficios adicionales...? | Beneficios inesperados | Texto libre |\n| ¿Qué problemas o dificultades...? | Desafíos enfrentados | Texto libre |\n| Procesado | Marca de procesamiento | Columna L (vacía/Sí/No) |",
        "feedback_auto_conversions_subheader": "🔄 Conversiones Automáticas",
        "feedback_satisfaction_conversion_markdown": "**Satisfacción:** Directo 1-10",
        "feedback_time_saved_conversion_markdown": "**Tiempo Ahorrado:** 1-10 → 0-100%",
        "feedback_processing_history_subheader": "📋 Historial de Procesamiento",
        "feedback_no_projects_with_tracking": "📝 No hay proyectos con tracking aún",
        "feedback_load_error": "❌ Error cargando cuestionario",
        "feedback_missing_columns": "❌ Faltan columnas en el cuestionario",
        "feedback_mark_processed_error": "❌ Error marcando respuestas",
        # Seguimiento
        "post_implementation": "Seguimiento Post-Implementación",
        "select_project": "Seleccionar Proyecto",
        "no_projects_warning": "⚠️ No hay proyectos. Ve a Planificación para crear uno.",
        "tracking_data": "Datos de Seguimiento",
        "months_tracked": "Meses de seguimiento",
        "actual_time_task": "Tiempo real por tarea (hrs)",
        "before_label": "Antes",
        "actual_tasks_month": "Tareas reales por mes",
        "projected_label": "Proyectado",
        "adoption_satisfaction": "Adopción y Satisfacción",
        "adoption_rate": "Tasa de adopción (%)",
        "adoption_help": "% del equipo que usa la automatización",
        "user_satisfaction": "Satisfacción del usuario (1-10)",
        "satisfaction_help": "Encuesta a usuarios finales",
        "unexpected_benefits": "Beneficios inesperados",
        "unexpected_benefits_placeholder": "Beneficios que no se anticiparon inicialmente...",
        "challenges_faced": "Desafíos enfrentados",
        "challenges_placeholder": "Problemas o dificultades durante la implementación...",
        "lessons_learned": "Lecciones aprendidas",
        "lessons_placeholder": "Qué haríamos diferente la próxima vez...",
        "save_tracking_btn": "💾 Guardar Seguimiento",
        "tracking_saved": "✅ Seguimiento guardado",
        # Resultados de seguimiento
        "real_performance": "Performance Real",
        "excellent_performance": "🎉 Excelente! El proyecto superó las expectativas",
        "good_performance": "✅ Buen rendimiento, cumplió objetivos",
        "moderate_performance": "⚠️ Rendimiento moderado, hay margen de mejora",
        "low_performance": "🔴 Bajo rendimiento, requiere análisis de causas",
        "expected_vs_real": "Esperado vs Real",
        "expected_reduction": "Reducción Esperada",
        "real_reduction": "Reducción Real",
        "expected_savings_month": "Ahorros Esperados/mes",
        "real_savings_month": "Ahorros Reales/mes",
        "project_efficiency": "Eficiencia del Proyecto",
        "exceeded_significantly": "Superó expectativas significativamente",
        "met_expectations": "Cumplió o superó expectativas",
        "close_expectations": "Cerca de las expectativas",
        "below_expectations": "Por debajo de las expectativas",
        # Dashboard
        "general_dashboard": "Dashboard General",
        "no_projects_dashboard": "⚠️ No hay proyectos para mostrar",
        "avg_score": "Score Promedio",
        "total_savings": "Ahorro Total",
        "all_projects": "Todos los Proyectos",
        "project_name_col": "Nombre",
        "score_col": "Score",
        "annual_savings_col": "Ahorro Anual",
        "status_col": "Estado",
        # Estados de proyecto
        "status_planning": "planificación",
        "status_implemented": "implementado",
        # Información financiera separada
        "financial_info_note": "💡 **Nota:** Los datos financieros son informativos y no afectan el score de viabilidad.",
        "financial_justification": "Esta información te ayuda a justificar la inversión después de que el proyecto pase el filtro de factibilidad.",
        # Nuevos factores explicación
        "new_scoring_explanation": """🎯 **Nuevo Sistema de Scoring (100 puntos):**
- ⚡ **Factor de Impacto (35 puntos):** ¿Cuánto tiempo ahorro?
- ⚠️ **Factor de Riesgo (30 puntos):** ¿Qué tan difícil técnicamente?
- 🔧 **Factor de Complejidad (35 puntos):** ¿Qué tan difícil implementar?

**El score evalúa: "¿Es factible y tiene impacto?"**""",
    },
    "pt": {
        # Header y navegación
        "page_title": "Avaliador de Viabilidade - Projetos IA/Automação",
        "main_title": "Avaliador de Viabilidade de Projetos",
        "main_subtitle": "Analise a viabilidade técnica dos seus projetos de IA e automação",
        "language_label": "🌍 Idioma",
        "planning_tab": "📋 Planejamento",
        "viability_tab": "Viabilidade",
        "operational_log_tab": "Registro",
        "impact_kpis_tab": "Impacto & KPIs",
        "tracking_tab": "📊 Acompanhamento Pós-Implementação",
        "dashboard_tab": "📈 Dashboard",
        "use_case_matrix_tab": "Matriz Impacto-Esforço",
        "feedback_tab": "Feedback",
        "sql_tab": "SQL",
        "platform_title": "Plataforma Integrada de Gestão de Projetos de Automação",
        "platform_subtitle": "Planeje, avalie, acompanhe e analise projetos de IA e automação em um só lugar.",
        # Gestión de archivos
        "file_management": "📁 Gestão de Arquivos",
        "upload_excel": "📤 Carregar Excel existente",
        "upload_help": "Suba um arquivo Excel com dados anteriores",
        "load_data_btn": "🔄 Carregar dados",
        "data_loaded": "✅ Dados carregados com sucesso",
        "generate_excel_btn": "💾 Gerar Excel para SharePoint",
        "download_excel_btn": "📥 Baixar Excel",
        "sharepoint_steps": """📋 **Passos para SharePoint:**
1. Baixe o arquivo Excel
2. Suba para seu site SharePoint
3. Compartilhe o link com a equipe
4. Todos podem baixar, editar e reenviar""",
        "save_local_btn": "💿 Salvar localmente",
        "saved_local": "✅ Salvo em project_viability.xlsx",
        # Búsqueda de proyectos
        "search_projects": "🔍 Buscar Projetos",
        "search_placeholder": 'ex: a1b2c3d4 ou "lead scoring"',
        "projects_found": "projeto(s) encontrado(s)",
        "no_projects_found": "⚠️ Nenhum projeto encontrado",
        "edit_btn": "📝 Editar",
        # Estadísticas sidebar
        "statistics": "📊 Estatísticas",
        "total_projects": "Projetos",
        "total_trackings": "Acompanhamentos",
        "high_priority": "Alta Prioridade",
        "implemented": "Implementados",
        "executing": "Em execução",
        # Formulario de proyecto
        "project_info": "Informações do Projeto",
        "project_name": "Nome do Projeto",
        "project_name_placeholder": "ex: Automação de lead scoring",
        "project_description": "Descrição",
        "project_description_placeholder": "Breve descrição do projeto...",
        "current_situation": "Situação Atual",
        "time_per_task": "Tempo por tarefa (hrs)",
        "tasks_per_month": "Tarefas por mês",
        "staff_count": "Pessoal envolvido",
        "salary_scale": "Scale Salarial",
        "dev_salary_scale": "Scale do Desenvolvedor",
        "salary_custom": "Personalizado",
        "cost_per_hour": "Custo por hora (USD)",
        # Scale levels (sin horas visibles)
        "scale_levels": {
            "Scale 40": "Scale 40",
            "Scale 50": "Scale 50",
            "Scale 60": "Scale 60",
            "Scale 70": "Scale 70",
            "Scale 80": "Scale 80",
            "Scale 90": "Scale 90",
            "Personalizado": "Personalizado",
        },
        # Mejoras esperadas
        "expected_improvements": "Melhorias Esperadas",
        "time_reduction": "Redução de tempo (%)",
        # Costos del proyecto
        "project_costs": "Custos do Projeto",
        "development_hours": "Horas de desenvolvimento",
        "monthly_maintenance": "Manutenção mensal (USD)",
        # Factores de riesgo (selectores simples)
        "risk_factors": "Fatores de Risco",
        "implementation_complexity": "Complexidade de implementação (1-5)",
        "technical_risk": "Nível de risco técnico (1-5)",
        # Opciones simples para complejidad
        "complexity_options": {
            1: "1 - Muito simples",
            2: "2 - Simples",
            3: "3 - Moderada",
            4: "4 - Complexa",
            5: "5 - Muito complexa",
        },
        # Opciones simples para riesgo
        "risk_options": {1: "1 - Muito baixo", 2: "2 - Baixo", 3: "3 - Médio", 4: "4 - Alto", 5: "5 - Muito alto"},
        # Botones principales
        "create_project_btn": "💾 Criar Projeto",
        "update_project_btn": "🔄 Atualizar Projeto",
        "new_project_btn": "➕ Novo Projeto",
        "search_edit_btn": "🔍 Buscar/Editar",
        "cancel_btn": "❌ Cancelar",
        # Resultados y scoring
        "viability_score": "Score de Viabilidade",
        "priority": "Prioridade",
        "financial_analysis": "Análise Financeira",
        "monthly_savings": "Economia Mensal",
        "annual_savings": "Economia Anual",
        "initial_investment": "Investimento Inicial",
        "payback_period": "Recuperação",
        "efficiency_improvements": "Melhorias de Eficiência",
        "hours_saved_month": "Horas economizadas por mês",
        "time_reduction_achieved": "Redução de tempo",
        "first_year_roi": "ROI primeiro ano",
        # Estados y prioridades
        "priority_high": "Alta",
        "priority_medium_high": "Média-Alta",
        "priority_medium": "Média",
        "priority_low": "Baixa",
        # Recomendaciones del nuevo sistema
        "recommendation_80_100": "Projeto altamente viável. Excelente impacto e baixa complexidade.",
        "recommendation_60_79": "Projeto viável. Bom impacto com risco controlado.",
        "recommendation_40_59": "Projeto marginal. Avaliar simplificação antes de prosseguir.",
        "recommendation_0_39": "Projeto não recomendado. Alto risco ou complexidade excessiva.",
        # Mensajes de éxito/error
        "project_created": "✅ Projeto criado",
        "project_updated": "✅ Projeto atualizado",
        "error_occurred": "❌ Erro",
        "name_required": "❌ Nome do projeto é obrigatório",
        "project_in_memory": "✅ Projeto na Memória",
        "created_date": "Criado",
        "status": "Status",
        "create_search_prompt": "👆 Criar ou buscar um projeto para ver os resultados aqui",
        "project_not_found": "❌ Projeto não encontrado",
        "project_label": "Projeto",
        "project_id_pending": "Será gerado ao salvar",
        "na": "N/D",
        "current_score": "Score atual",
        "loop_label": "Loop",
        "open_loop_btn": "Abrir Loop",
        "no_link": "Sem link",
        "evaluation_form": "Formulário de avaliação",
        "owner_help": "Usado para gerar ID no padrão PAIS-OWNER-NNNN",
        "owner_label": "Owner",
        "country_iso2": "Country (ISO2)",
        "financial_average_rate_caption": "💡 Cálculos financeiros com hora média:",
        "optional_details": "Detalhes opcionais",
        "scale_reference_help": "Não afeta os cálculos de ROI.",
        "developer_team_label": "Time de desenvolvimento",
        "loop_url_label": "Loop URL",
        "loop_optional_viability_note": "Opcional na Viabilidade. Deve ser preenchido no Registro (primeira entrada).",
        "save_evaluation_status_label": "Estado ao salvar avaliação",
        "action_owner_label": "Responsável pela ação",
        "evaluate_btn": "🧮 Avaliar",
        "save_evaluation_btn": "💾 Salvar avaliação",
        "approve_to_agenda_btn": "✅ Aprovar (ir para agenda)",
        "owner_required": "Owner é obrigatório para gerar o ID do projeto.",
        "evaluation_calculated_not_saved": "Avaliação calculada. Não foi salva no banco.",
        "loop_required_for_approval": "Para aprovar, registre o link do Loop.",
        "project_approved_sent_to_agenda": "Projeto aprovado e enviado para agenda.",
        "folder_provisioned_ok": "📁 Pasta criada: {path} (cor: {color})",
        "folder_provisioned_warning": "⚠️ Projeto aprovado mas não foi possível criar a pasta: {error}",
        "evaluation_saved_msg": "Avaliação salva.",
        "evaluate_to_view_results_info": "Avalie um projeto para ver resultados. Avaliar não persiste; Salvar/Aprovar sim.",
        "temporary_results_warning": "Resultados temporários: ainda não persistidos.",
        "persisted_results_success": "Resultados persistidos.",
        "sql_tab_header": "🗄️ Consultas SQL",
        "sql_tab_caption": "Execute consultas SELECT no banco SQLite local.",
        "sql_available_tables_markdown": "Tabelas disponíveis:\n- `projects`\n- `tracking`",
        "sql_query_input_label": "Consulta SQL (somente leitura)",
        "sql_run_select_btn": "▶ Executar SELECT",
        "sql_clear_btn": "🧹 Limpar",
        "sql_download_csv_btn": "📥 Baixar resultado (CSV)",
        "sql_error_empty": "A consulta está vazia.",
        "sql_error_single_statement": "Somente uma sentença SQL é permitida.",
        "sql_error_readonly": "Somente consultas SELECT são permitidas (incluindo WITH ... SELECT).",
        "sql_error_forbidden_keyword": "Consulta bloqueada por palavra reservada não permitida:",
        "sql_error_running_query": "Erro ao executar consulta",
        "sql_query_ok_rows": "Consulta executada. Linhas:",
        "ucm_header": "Matriz Impacto-Esforço",
        "ucm_schema_init_error": "Não foi possível inicializar o esquema da matriz",
        "ucm_load_portfolio_error": "Não foi possível carregar o portfólio",
        "ucm_no_saved_projects": "Não há projetos salvos (Salvar avaliação / Aprovar).",
        "ucm_no_scores_filtered": "Não há scores de Impact/Effort para os filtros selecionados.",
        "ucm_year_filter": "Ano",
        "ucm_team_filter": "Equipe",
        "ucm_no_team": "Sem equipe",
        "ucm_status_filter": "Status",
        "ucm_search_filter": "Busca (nome, owner, project_id)",
        "ucm_detail_title": "Detalhe do projeto",
        "ucm_no_detail_results": "Sem resultados para mostrar detalhe.",
        "ucm_select_project": "Selecione projeto",
        "ucm_open_viability_btn": "Abrir em Viabilidade",
        "ucm_open_viability_hint": "Projeto carregado no session_state. Vá para a aba 'Viabilidade'.",
        "ucm_change_status": "Alterar status",
        "ucm_save_status_btn": "Salvar status",
        "ucm_status_updated": "Status atualizado para",
        "ucm_status_update_error": "Não foi possível atualizar o status",
        "ucm_filtered_dataset": "Dataset filtrado",
        "download_csv": "Baixar CSV",
        "download_json": "Baixar JSON",
        "ops_projects_table_missing": "A tabela projects não existe. Crie projetos primeiro em Viabilidade.",
        "ops_demo_loaded": "Dados demo carregados.",
        "ops_demo_load_error": "Não foi possível carregar demo",
        "ops_last_notes_title": "Últimas notas do projeto",
        "ops_no_note": "Sem nota",
        "ops_tags_label": "Tags",
        "ops_quick_capture": "Captura rápida",
        "ops_included_statuses": "Status incluídos",
        "ops_no_eligible_projects": "Não há projetos elegíveis para captura rápida.",
        "ops_no_notes": "Sem notas",
        "ops_last_update": "Última atualização",
        "ops_progress_last_value": "Último avanço",
        "ops_progress_last_date": "Data do último avanço",
        "ops_progress_no_data": "Sem dados de avanço",
        "ops_progress_capture_enable": "Registrar % de avanço nesta atualização",
        "ops_progress_percent_label": "% de avanço do projeto",
        "ops_estimated_end_date_label": "Data estimada de encerramento (opcional)",
        "ops_progress_suggested": "Progresso sugerido com base nos dias transcorridos",
        "ops_progress_trend": "Tendência de avanço",
        "ops_progress_drop_warning": "O progresso caiu sem justificativa visível:",
        "ops_progress_overview_title": "Avanço por projeto",
        "ops_first_entry_loop_required": "Primeira entrada do projeto: o link do Loop é obrigatório antes de salvar a atualização.",
        "ops_loop_missing_warning": "Este projeto ainda não possui link do Loop. Configure para continuar registrando entradas.",
        "ops_loop_doc_link": "Link de documentação (Loop)",
        "ops_save_link_btn": "Salvar link",
        "ops_link_updated": "Link atualizado.",
        "ops_link_save_error": "Não foi possível salvar link",
        "ops_note_title_optional": "Título da atualização (opcional)",
        "ops_recent_tags": "Tags recentes",
        "ops_extra_tags_csv": "Tags extras (CSV)",
        "ops_extra_tags_placeholder": "comercial,etl,pendente",
        "ops_author": "Autor",
        "ops_save_update_btn": "Salvar atualização",
        "ops_author_required": "O autor é obrigatório.",
        "ops_loop_required_to_save": "Você deve informar o link do Loop para salvar a atualização.",
        "ops_no_content_to_save": "Não há conteúdo para salvar. Preencha pelo menos uma seção.",
        "ops_update_saved": "Atualização salva. Grupo:",
        "ops_notes_inserted": "Notas inseridas",
        "ops_save_update_error": "Erro ao salvar atualização",
        "ops_executive_summary": "Resumo executivo",
        "ops_states": "Status",
        "ops_search": "Busca",
        "ops_days_without_update": "Dias sem update (>=)",
        "ops_summary_build_error": "Não foi possível montar o resumo",
        "ops_no_results_filters": "Não há resultados para os filtros selecionados.",
        "ops_update_title": "Atualização",
        "ops_timeline_history": "Timeline / Histórico",
        "ops_project_timeline_select": "Projeto (timeline por projeto)",
        "ops_search_text": "Buscar texto",
        "ops_filter_tag": "Filtrar tag",
        "ops_type": "Tipo",
        "ops_all": "Todos",
        "ops_limit": "Limite",
        "ops_from": "De",
        "ops_to": "Até",
        "ops_project_view": "Visão por projeto",
        "ops_no_project_notes_filtered": "Não há notas para o projeto com os filtros selecionados.",
        "ops_project_timeline_label": "timeline projeto",
        "ops_global_view": "Visão global",
        "ops_no_global_notes_filtered": "Não há notas globais com os filtros selecionados.",
        "ops_global_timeline_label": "timeline global",
        "ops_tab_caption": "Notas imutáveis por projeto. V2 com captura rápida, resumo executivo e timeline.",
        "ops_schema_init_error": "Não foi possível inicializar esquema",
        "ops_load_demo": "Carregar dados demo",
        "ops_error_quick_capture": "Erro em Captura rápida",
        "ops_error_executive_summary": "Erro em Resumo executivo",
        "ops_error_timeline": "Erro em Timeline / Histórico",
        "ops_note_help_general": "Contexto, decisão e resultado.",
        "ops_note_help_next_step": "Ação concreta + responsável + data compromisso.",
        "ops_note_help_blocker": "Impedimento real + impacto + quem destrava.",
        "ops_note_help_risk": "Risco potencial + probabilidade + mitigação.",
        "ops_note_example_general": 'Exemplo: "Escopo validado com Comercial e TI".',
        "ops_note_example_next_step": 'Exemplo: "Enviar brief para TI - Ana - 12/03".',
        "ops_note_example_blocker": 'Exemplo: "Sem acesso à API; suporte TI destrava".',
        "ops_note_example_risk": 'Exemplo: "Risco de mudança de owner; mitigar com handoff documentado".',
        "ops_capture_help_info": 'Guia rápido:\n- Geral: contexto e decisão. Exemplo: "Escopo validado com Comercial".\n- Próximo passo: ação + responsável + data. Exemplo: "Enviar brief para TI - Ana - 12/03".\n- Bloqueador: o que impede e quem destrava. Exemplo: "Sem acesso à API - suporte TI".\n- Risco: possível problema e mitigação. Exemplo: "Mudança de owner; documentar handoff".',
        "project_links_section": "Acessos do projeto",
        "loop_link": "Link do Loop",
        "repo_link": "Link do Repo",
        "artifacts_link": "Link de Artefatos",
        "open_repo_btn": "Abrir Repo",
        "open_artifacts_btn": "Abrir Artefatos",
        "configure_links": "Configurar links",
        "save_links": "Salvar acessos",
        "ops_links_updated": "Acessos atualizados.",
        "ops_status_changed_to": "Status atualizado para",
        "repo_help": "Link para o repositório no Azure DevOps.",
        "artifacts_help": "Link para SharePoint/pasta/Power BI/outro.",
        "artifacts_type": "Tipo de artefato",
        "tech_stack": "Stack tecnológico",
        "artifacts_type_azure_devops": "Azure DevOps",
        "artifacts_type_sharepoint": "SharePoint",
        "artifacts_type_powerbi": "Power BI",
        "artifacts_type_excel_vba": "Excel/VBA",
        "artifacts_type_folder": "Pasta",
        "artifacts_type_agent": "Agente IA",
        "artifacts_type_other": "Outro",
        "tech_stack_python": "Python",
        "tech_stack_vba": "VBA",
        "tech_stack_powerbi": "Power BI",
        "tech_stack_agent": "Agente IA",
        "tech_stack_other": "Outro",
        "tracking_auto_data_info": "🤖 **Dados atualizados automaticamente via pesquisa.** Você pode ajustar manualmente se necessário.",
        "tracking_manual_or_wait_info": "✋ **Preencha manualmente** ou aguarde dados automáticos da pesquisa.",
        "tracking_update_btn": "🔄 Atualizar Tracking",
        "tracking_updated_manual": "🔄 Tracking atualizado manualmente",
        "tracking_auto_source": "🤖 Dados de pesquisa automática",
        "tracking_manual_source": "✋ Dados inseridos manualmente",
        "tracking_qualitative_analysis": "📝 Análise Qualitativa",
        "tracking_unexpected_benefits_expander": "✅ Benefícios Inesperados",
        "tracking_challenges_expander": "⚠️ Desafios Enfrentados",
        "tracking_lessons_expander": "💡 Lições Aprendidas",
        "tracking_recommendations": "🎯 Recomendações",
        "tracking_reco_replicate": "✅ Replicar esta abordagem em projetos similares",
        "tracking_reco_review_method": "⚠️ Revisar metodologia de estimativa para projetos futuros",
        "tracking_reco_change_training": "👥 Melhorar estratégias de mudança organizacional e treinamento",
        "tracking_reco_involve_users": "🎯 Envolver mais usuários finais no desenho das soluções",
        "tracking_reco_expand_scope": "🏆 Considerar expandir o escopo do projeto",
        "tracking_project_on_track": "🎉 O projeto está funcionando como esperado",
        "tracking_no_tracking_for_project": "📝 Ainda não há acompanhamentos para este projeto",
        "tracking_project_info_title": "📋 Informações do Projeto",
        "tracking_auto_when_feedback": "🤖 O tracking será preenchido automaticamente quando houver respostas da pesquisa",
        "tracking_fill_form_hint": "👆 Preencha o formulário à esquerda para iniciar o acompanhamento",
        "tracking_feedback_file_not_found": "Arquivo não encontrado",
        "tracking_feedback_missing_columns": "O arquivo não possui as colunas obrigatórias",
        "tracking_feedback_read_error": "Erro ao ler arquivo",
        "tracking_feedback_processed_ok": "✅ Novas respostas processadas:",
        "tracking_feedback_no_new": "📝 Arquivo encontrado, sem novas respostas para processar:",
        "tracking_unknown_error": "Erro desconhecido",
        "tracking_feedback_process_error": "❌ Erro ao processar",
        "tracking_auto_process_error": "❌ Erro no processamento automático",
        "tracking_source_no_tracking": "📝 Sem acompanhamento",
        "tracking_source_auto_survey": "🤖 Automático (pesquisa)",
        "tracking_source_manual": "✋ Manual",
        "tracking_source_no_data": "📝 Sem dados",
        "tracking_spinner_search_feedback": "🔍 Buscando atualizações de pesquisas...",
        "tracking_updated_projects_expander": "📊 Ver projeto(s) atualizado(s)",
        "tracking_satisfaction_label": "Satisfação",
        "tracking_time_saved_label": "Tempo economizado",
        "tracking_status_prefix": "📊 **Status do tracking**",
        "tracking_efficiency_label": "Eficiência",
        "tracking_no_implemented_warning": "Não há projetos implementados para acompanhamento pós-implementação.",
        "dashboard_scores_distribution": "📊 Distribuição de Scores",
        "dashboard_priority_distribution": "🎯 Distribuição por Prioridade",
        "dashboard_viability_vs_roi": "📈 Score de Viabilidade vs ROI",
        "dashboard_factor_analysis": "🔍 Análise de Fatores",
        "dashboard_tracking_metrics": "📊 Métricas de Acompanhamento",
        "dashboard_scatter_caption": "💡 Pontos acima da linha vermelha indicam projetos que superaram as expectativas iniciais",
        "dashboard_portfolio_insights": "💡 Insights do Portfólio",
        "dashboard_add_more_for_insights": "📈 Continue adicionando projetos e acompanhamentos para obter insights personalizados",
        "dashboard_export_excel_btn": "📥 Exportar Dashboard como Excel",
        "dashboard_scores_distribution_title": "Distribuição de Scores de Viabilidade",
        "dashboard_num_projects": "Número de Projetos",
        "dashboard_projects_by_priority": "Projetos por Prioridade",
        "dashboard_viability_roi_relation": "Relação entre Score de Viabilidade e ROI",
        "dashboard_complexity_distribution_title": "Distribuição por Complexidade",
        "dashboard_complexity_level": "Nível de Complexidade (1-5)",
        "dashboard_technical_risk_distribution_title": "Distribuição por Risco Técnico",
        "dashboard_risk_level": "Nível de Risco (1-5)",
        "dashboard_avg_performance": "Performance Média",
        "dashboard_avg_efficiency": "Eficiência Média",
        "dashboard_avg_adoption": "Adoção Média",
        "dashboard_avg_satisfaction": "Satisfação Média",
        "dashboard_initial_vs_real_performance": "Score Inicial vs Performance Real",
        "dashboard_initial_viability_score": "Score de Viabilidade Inicial",
        "dashboard_real_performance_percent": "Performance Real (%)",
        "dashboard_insight_portfolio_solid": "🎯 **Portfólio sólido**: Mais de 50% dos projetos têm alta viabilidade",
        "dashboard_insight_high_complexity": "⚠️ **Alta complexidade**: Considere simplificar alguns projetos para melhor execução",
        "dashboard_insight_implementation_success": "✅ **Implementação bem-sucedida**: A maioria dos projetos executados supera expectativas",
        "feedback_processor_header": "📊 Processador de Questionários de Feedback",
        "feedback_processor_how_it_works": "**Como funciona?**\n\n1. 📤 **Envie o Excel** do questionário com respostas\n2. 🔄 **Processamento automático:** Converte respostas em dados de tracking\n3. 📊 **Atualização:** Os projetos são atualizados com dados reais\n4. ✅ **Marcação:** As respostas processadas são marcadas para evitar duplicidade",
        "feedback_tab_upload": "📤 Enviar Questionário",
        "feedback_tab_preview": "🔍 Preview Dados",
        "feedback_tab_history": "📋 Histórico",
        "feedback_upload_file_subheader": "📤 Enviar Arquivo de Questionário",
        "feedback_select_excel_label": "Selecione o Excel do questionário",
        "feedback_select_excel_help": "Arquivo com respostas do questionário de feedback",
        "feedback_preview_data_expander": "👀 Preview dos Dados",
        "feedback_total_responses": "Total de respostas:",
        "feedback_process_btn": "🚀 Processar Questionário",
        "feedback_processing_spinner": "Processando respostas...",
        "feedback_processing_success": "✅ Processamento concluído com sucesso!",
        "feedback_total_responses_metric": "Respostas Totais",
        "feedback_processed_responses_metric": "Respostas Processadas",
        "feedback_updated_projects_metric": "Projetos Atualizados",
        "feedback_updated_projects_subheader": "📊 Projetos Atualizados",
        "feedback_responses_metric": "Respostas",
        "feedback_satisfaction_metric": "Satisfação",
        "feedback_time_saved_metric": "Tempo Economizado",
        "feedback_warnings_found": "⚠️ Alguns problemas encontrados:",
        "feedback_preview_questionnaire_subheader": "🔍 Preview de Dados do Questionário",
        "feedback_expected_excel_structure_markdown": "**Estrutura esperada do Excel:**\n\n| Coluna | Descrição | Formato |\n|---------|-------------|---------|\n| ID DEL PROYECTO | Identificador do projeto | Texto (ex: a1b2c3d4) |\n| ¿Qué tan satisfecho/a estás...? | Satisfação do usuário | Número 1-10 |\n| ¿Qué porcentaje de tiempo...? | Tempo economizado | Número 1-10 (convertido para %) |\n| ¿Qué beneficios adicionales...? | Benefícios inesperados | Texto livre |\n| ¿Qué problemas o dificultades...? | Desafios enfrentados | Texto livre |\n| Procesado | Marca de processamento | Coluna L (vazia/Sim/Não) |",
        "feedback_auto_conversions_subheader": "🔄 Conversões Automáticas",
        "feedback_satisfaction_conversion_markdown": "**Satisfação:** Direto 1-10",
        "feedback_time_saved_conversion_markdown": "**Tempo Economizado:** 1-10 → 0-100%",
        "feedback_processing_history_subheader": "📋 Histórico de Processamento",
        "feedback_no_projects_with_tracking": "📝 Ainda não há projetos com tracking",
        "feedback_load_error": "❌ Erro ao carregar questionário",
        "feedback_missing_columns": "❌ Faltam colunas no questionário",
        "feedback_mark_processed_error": "❌ Erro ao marcar respostas",
        # Seguimiento
        "post_implementation": "Acompanhamento Pós-Implementação",
        "select_project": "Selecionar Projeto",
        "no_projects_warning": "⚠️ Não há projetos. Vá para Planejamento para criar um.",
        "tracking_data": "Dados de Acompanhamento",
        "months_tracked": "Meses de acompanhamento",
        "actual_time_task": "Tempo real por tarefa (hrs)",
        "before_label": "Antes",
        "actual_tasks_month": "Tarefas reais por mês",
        "projected_label": "Projetado",
        "adoption_satisfaction": "Adoção e Satisfação",
        "adoption_rate": "Taxa de adoção (%)",
        "adoption_help": "% da equipe que usa a automação",
        "user_satisfaction": "Satisfação do usuário (1-10)",
        "satisfaction_help": "Pesquisa com usuários finais",
        "unexpected_benefits": "Benefícios inesperados",
        "unexpected_benefits_placeholder": "Benefícios que não foram antecipados inicialmente...",
        "challenges_faced": "Desafios enfrentados",
        "challenges_placeholder": "Problemas ou dificuldades durante a implementação...",
        "lessons_learned": "Lições aprendidas",
        "lessons_placeholder": "O que faríamos diferente na próxima vez...",
        "save_tracking_btn": "💾 Salvar Acompanhamento",
        "tracking_saved": "✅ Acompanhamento salvo",
        # Resultados de seguimiento
        "real_performance": "Performance Real",
        "excellent_performance": "🎉 Excelente! O projeto superou as expectativas",
        "good_performance": "✅ Bom desempenho, cumpriu objetivos",
        "moderate_performance": "⚠️ Desempenho moderado, há margem para melhoria",
        "low_performance": "🔴 Baixo desempenho, requer análise de causas",
        "expected_vs_real": "Esperado vs Real",
        "expected_reduction": "Redução Esperada",
        "real_reduction": "Redução Real",
        "expected_savings_month": "Economias Esperadas/mês",
        "real_savings_month": "Economias Reais/mês",
        "project_efficiency": "Eficiência do Projeto",
        "exceeded_significantly": "Superou expectativas significativamente",
        "met_expectations": "Cumpriu ou superou expectativas",
        "close_expectations": "Próximo das expectativas",
        "below_expectations": "Abaixo das expectativas",
        # Dashboard
        "general_dashboard": "Dashboard Geral",
        "no_projects_dashboard": "⚠️ Não há projetos para mostrar",
        "avg_score": "Score Médio",
        "total_savings": "Economia Total",
        "all_projects": "Todos os Projetos",
        "project_name_col": "Nome",
        "score_col": "Score",
        "annual_savings_col": "Economia Anual",
        "status_col": "Status",
        # Estados de proyecto
        "status_planning": "planejamento",
        "status_implemented": "implementado",
        # Información financiera separada
        "financial_info_note": "💡 **Nota:** Os dados financeiros são informativos e não afetam o score de viabilidade.",
        "financial_justification": "Esta informação ajuda a justificar o investimento depois que o projeto passa pelo filtro de viabilidade.",
        # Nuevos factores explicación
        "new_scoring_explanation": """🎯 **Novo Sistema de Scoring (100 pontos):**
- ⚡ **Fator de Impacto (35 pontos):** Quanto tempo economizo?
- ⚠️ **Fator de Risco (30 pontos):** Quão difícil tecnicamente?
- 🔧 **Fator de Complexidade (35 pontos):** Quão difícil implementar?

**O score avalia: "É viável e tem impacto?"**""",
    },
}

# t(), get_language(), TRANSLATIONS — imported from ui.i18n above


def get_scale_salary(scale_level):
    """Convierte scale level a salario por hora (INTERNO - no visible)"""
    scale_mapping = {"Scale 40": 7, "Scale 50": 10, "Scale 60": 15, "Scale 70": 24, "Scale 80": 35, "Scale 90": 50}
    return scale_mapping.get(scale_level, 25)


# =============================================================================
# CLASES PRINCIPALES
# =============================================================================


class ExcelSharePointManager:
    """Persistencia de proyectos/tracking usando SQLite, con import/export de Excel."""

    def __init__(self, file_url: str, username: str = None, password: str = None):
        self.file_url = file_url
        self.username = username
        self.password = password
        self.db_path = "project_viability.db"
        self.id_format = "{country}-{owner}-{sequence}"
        self.id_n_digits = 4
        self._load_id_config()

        # Estructura para proyectos
        self.project_columns = [
            "id",
            "name",
            "description",
            "created_date",
            "status",
            "last_tracking_update",
            "country",
            "owner",
            "current_time_per_task",
            "tasks_per_month",
            "staff_count",
            "avg_salary_per_hour",
            "time_reduction_percent",
            "development_hours",
            "development_cost_per_hour",
            "maintenance_monthly",
            "implementation_complexity",
            "risk_level",
            "viability_score",
            "priority",
            "monthly_savings",
            "annual_savings",
            "payback_period_months",
            "roi_first_year",
            "recommendation",
            "initial_development_cost",
            "hours_saved_per_month",
            "actual_monthly_savings",
            "actual_annual_savings",
        ]

        # Estructura para seguimientos
        self.tracking_columns = [
            "id",
            "project_id",
            "tracking_date",
            "months_tracked",
            "actual_time_per_task",
            "actual_tasks_per_month",
            "adoption_rate",
            "user_satisfaction_score",
            "unexpected_benefits",
            "challenges_faced",
            "lessons_learned",
            "performance_score",
            "efficiency_ratio",
            "actual_time_reduction_percent",
            "actual_monthly_savings",
            "actual_annual_savings",
        ]

        self.init_excel_structure()

    @property
    def projects_df(self):
        """Compatibilidad para módulos que esperan DataFrame de proyectos."""
        return self._read_table("projects")

    @property
    def tracking_df(self):
        """Compatibilidad para módulos que esperan DataFrame de tracking."""
        return self._read_table("tracking")

    def _get_connection(self):
        return sqlite3.connect(self.db_path)

    def _load_id_config(self):
        """Carga configuracion de formato de ID desde config/scoring_config.json."""
        config_path = os.path.join("config", "scoring_config.json")
        try:
            with open(config_path, "r", encoding="utf-8") as f:
                cfg = json.load(f)
            self.id_format = str(cfg.get("id_format", self.id_format))
            self.id_n_digits = int(cfg.get("n_digits", self.id_n_digits))
        except Exception:
            pass

    def _normalize_country(self, value: str) -> str:
        return (value or "").strip().upper()[:2]

    def _normalize_owner(self, value: str) -> str:
        return re.sub(r"[^A-Z0-9_]", "", (value or "").strip().upper())

    def _id_regex(self):
        escaped = re.escape(self.id_format)
        escaped = escaped.replace(r"\{country\}", r"([A-Z]{2})")
        escaped = escaped.replace(r"\{owner\}", r"([A-Z0-9_]+)")
        escaped = escaped.replace(r"\{sequence\}", rf"(\d{{{self.id_n_digits}}})")
        return re.compile(rf"^{escaped}$")

    def _generate_next_project_id(self, country: str, owner: str) -> str:
        country = self._normalize_country(country) or "NA"
        owner = self._normalize_owner(owner) or "GEN"

        regex = self._id_regex()
        max_seq = 0

        with self._get_connection() as conn:
            rows = conn.execute("SELECT id FROM projects").fetchall()

        for (project_id,) in rows:
            if not project_id:
                continue
            match = regex.match(str(project_id))
            if not match:
                continue
            row_country, row_owner, row_seq = match.group(1), match.group(2), match.group(3)
            if row_country == country and row_owner == owner:
                max_seq = max(max_seq, int(row_seq))

        sequence = f"{max_seq + 1:0{self.id_n_digits}d}"
        return self.id_format.format(country=country, owner=owner, sequence=sequence)

    def _read_table(self, table_name: str) -> pd.DataFrame:
        with self._get_connection() as conn:
            return pd.read_sql_query(f"SELECT * FROM {table_name}", conn)

    def _replace_table_from_df(self, table_name: str, df: pd.DataFrame, expected_columns: list):
        normalized = df.copy()
        for col in expected_columns:
            if col not in normalized.columns:
                normalized[col] = None
        normalized = normalized[expected_columns]

        with self._get_connection() as conn:
            conn.execute(f"DELETE FROM {table_name}")
            normalized.to_sql(table_name, conn, if_exists="append", index=False)

    def init_excel_structure(self):
        """Inicializa la estructura base en SQLite"""
        with self._get_connection() as conn:
            conn.execute("""
                CREATE TABLE IF NOT EXISTS projects (
                    id TEXT PRIMARY KEY,
                    name TEXT,
                    description TEXT,
                    created_date TEXT,
                    status TEXT,
                    last_tracking_update TEXT,
                    country TEXT,
                    owner TEXT,
                    current_time_per_task REAL,
                    tasks_per_month INTEGER,
                    staff_count INTEGER,
                    avg_salary_per_hour REAL,
                    time_reduction_percent REAL,
                    development_hours REAL,
                    development_cost_per_hour REAL,
                    maintenance_monthly REAL,
                    implementation_complexity INTEGER,
                    risk_level INTEGER,
                    viability_score REAL,
                    priority TEXT,
                    monthly_savings REAL,
                    annual_savings REAL,
                    payback_period_months REAL,
                    roi_first_year REAL,
                    recommendation TEXT,
                    initial_development_cost REAL,
                    hours_saved_per_month REAL,
                    actual_monthly_savings REAL,
                    actual_annual_savings REAL
                )
            """)
            conn.execute("""
                CREATE TABLE IF NOT EXISTS tracking (
                    id TEXT PRIMARY KEY,
                    project_id TEXT,
                    tracking_date TEXT,
                    months_tracked INTEGER,
                    actual_time_per_task REAL,
                    actual_tasks_per_month INTEGER,
                    adoption_rate REAL,
                    user_satisfaction_score REAL,
                    unexpected_benefits TEXT,
                    challenges_faced TEXT,
                    lessons_learned TEXT,
                    performance_score REAL,
                    efficiency_ratio REAL,
                    actual_time_reduction_percent REAL,
                    actual_monthly_savings REAL,
                    actual_annual_savings REAL
                )
            """)
            conn.execute("CREATE INDEX IF NOT EXISTS idx_tracking_project_id ON tracking(project_id)")
            self._ensure_projects_schema(conn)

    def _ensure_projects_schema(self, conn):
        """Agrega columnas faltantes en instalaciones existentes."""
        existing_cols = {row[1] for row in conn.execute("PRAGMA table_info(projects)").fetchall()}
        required_cols = {
            "country": "TEXT",
            "owner": "TEXT",
            "initial_development_cost": "REAL",
            "hours_saved_per_month": "REAL",
        }
        for col_name, col_type in required_cols.items():
            if col_name not in existing_cols:
                conn.execute(f"ALTER TABLE projects ADD COLUMN {col_name} {col_type}")

    def load_from_local_excel(self, file_path: str = "project_viability.xlsx"):
        """Importa datos desde Excel local hacia SQLite."""
        try:
            projects_df = pd.read_excel(file_path, sheet_name="Projects")
            tracking_df = pd.read_excel(file_path, sheet_name="Tracking")
            self._replace_table_from_df("projects", projects_df, self.project_columns)
            self._replace_table_from_df("tracking", tracking_df, self.tracking_columns)
            return True
        except FileNotFoundError:
            st.info("📄 Archivo Excel no encontrado, creando estructura nueva")
            self.init_excel_structure()
            return False
        except Exception as e:
            st.error(f"❌ Error cargando Excel: {str(e)}")
            self.init_excel_structure()
            return False

    def save_to_local_excel(self, file_path: str = "project_viability.xlsx"):
        """Exporta datos actuales de SQLite a Excel."""
        try:
            projects_df = self.projects_df
            tracking_df = self.tracking_df
            with pd.ExcelWriter(file_path, engine="openpyxl") as writer:
                projects_df.to_excel(writer, sheet_name="Projects", index=False)
                tracking_df.to_excel(writer, sheet_name="Tracking", index=False)
            return True
        except Exception as e:
            st.error(f"❌ Error guardando Excel: {str(e)}")
            return False

    def upload_to_sharepoint_manual(self):
        """Genera Excel en memoria para subida manual a SharePoint."""
        buffer = io.BytesIO()
        projects_df = self.projects_df
        tracking_df = self.tracking_df

        with pd.ExcelWriter(buffer, engine="openpyxl") as writer:
            projects_df.to_excel(writer, sheet_name="Projects", index=False)
            tracking_df.to_excel(writer, sheet_name="Tracking", index=False)

        buffer.seek(0)
        return buffer

    def load_from_uploaded_file(self, uploaded_file):
        """Importa datos desde archivo subido (Excel) hacia SQLite."""
        try:
            projects_df = pd.read_excel(uploaded_file, sheet_name="Projects")
            tracking_df = pd.read_excel(uploaded_file, sheet_name="Tracking")
            self._replace_table_from_df("projects", projects_df, self.project_columns)
            self._replace_table_from_df("tracking", tracking_df, self.tracking_columns)
            return True
        except Exception as e:
            st.error(f"❌ Error procesando archivo: {str(e)}")
            return False

    def add_project(self, project_data: dict) -> str:
        """Añade un nuevo proyecto"""
        country = self._normalize_country(project_data.get("country", ""))
        owner = self._normalize_owner(project_data.get("owner", ""))
        project_id = self._generate_next_project_id(country, owner)
        project_data["id"] = project_id
        project_data["country"] = country or "NA"
        project_data["owner"] = owner or "GEN"
        project_data["created_date"] = datetime.now().isoformat()
        project_data["status"] = "planning"
        record = {col: project_data.get(col) for col in self.project_columns}
        columns_str = ", ".join(record.keys())
        placeholders = ", ".join(["?"] * len(record))

        with self._get_connection() as conn:
            conn.execute(f"INSERT INTO projects ({columns_str}) VALUES ({placeholders})", tuple(record.values()))

        return project_id

    def update_project(self, project_id: str, project_data: dict) -> bool:
        """Actualiza un proyecto existente"""
        try:
            valid_updates = {k: v for k, v in project_data.items() if k in self.project_columns and k != "id"}
            if not valid_updates:
                return True

            set_clause = ", ".join([f"{k} = ?" for k in valid_updates.keys()])
            params = list(valid_updates.values()) + [project_id]

            with self._get_connection() as conn:
                cur = conn.execute(f"UPDATE projects SET {set_clause} WHERE id = ?", params)
                return cur.rowcount > 0

        except Exception as e:
            st.error(f"❌ Error actualizando proyecto: {str(e)}")
            return False

    def project_exists(self, project_id: str) -> bool:
        """Verifica si un proyecto existe"""
        with self._get_connection() as conn:
            cur = conn.execute("SELECT 1 FROM projects WHERE id = ? LIMIT 1", (project_id,))
            return cur.fetchone() is not None

    def search_projects(self, search_term: str) -> list:
        """Busca proyectos por ID, nombre o descripción"""
        if not search_term:
            return self.get_all_projects()
        pattern = f"%{search_term}%"
        with self._get_connection() as conn:
            query = """
                SELECT * FROM projects
                WHERE id LIKE ? OR name LIKE ? OR description LIKE ?
                ORDER BY created_date DESC
            """
            df = pd.read_sql_query(query, conn, params=(pattern, pattern, pattern))
            return df.to_dict("records")

    def add_tracking(self, tracking_data: dict) -> str:
        """Añade seguimiento a un proyecto"""
        tracking_id = str(uuid.uuid4())[:8]
        tracking_data["id"] = tracking_id
        tracking_data["tracking_date"] = datetime.now().isoformat()
        record = {col: tracking_data.get(col) for col in self.tracking_columns}
        columns_str = ", ".join(record.keys())
        placeholders = ", ".join(["?"] * len(record))
        project_id = tracking_data["project_id"]

        with self._get_connection() as conn:
            conn.execute(f"INSERT INTO tracking ({columns_str}) VALUES ({placeholders})", tuple(record.values()))
            conn.execute("UPDATE projects SET status = ? WHERE id = ?", ("implemented", project_id))

        return tracking_id

    def update_project_from_tracking(self, project_id: str, tracking_results: dict):
        """Actualiza métricas del proyecto basado en resultados reales de tracking"""
        try:
            updates = {"status": "implemented", "last_tracking_update": datetime.now().isoformat()}

            if "actual_monthly_savings" in tracking_results:
                updates["actual_monthly_savings"] = tracking_results["actual_monthly_savings"]
                updates["actual_annual_savings"] = tracking_results.get("actual_annual_savings")

            set_clause = ", ".join([f"{k} = ?" for k in updates.keys()])
            params = list(updates.values()) + [project_id]

            with self._get_connection() as conn:
                cur = conn.execute(f"UPDATE projects SET {set_clause} WHERE id = ?", params)
                return cur.rowcount > 0

        except Exception as e:
            st.error(f"❌ Error actualizando proyecto desde tracking: {str(e)}")
            return False

    def get_all_projects(self) -> list:
        """Obtiene todos los proyectos como lista de diccionarios"""
        with self._get_connection() as conn:
            df = pd.read_sql_query("SELECT * FROM projects ORDER BY created_date DESC", conn)
            return df.to_dict("records")

    def get_project(self, project_id: str) -> dict:
        """Obtiene un proyecto específico"""
        with self._get_connection() as conn:
            df = pd.read_sql_query("SELECT * FROM projects WHERE id = ? LIMIT 1", conn, params=(project_id,))
            return df.iloc[0].to_dict() if not df.empty else None

    def get_project_tracking(self, project_id: str) -> list:
        """Obtiene seguimientos de un proyecto"""
        with self._get_connection() as conn:
            df = pd.read_sql_query(
                "SELECT * FROM tracking WHERE project_id = ? ORDER BY tracking_date ASC", conn, params=(project_id,)
            )
            return df.to_dict("records")


from ui.calculator import ProjectViabilityCalculator as _BaseCalculator  # noqa: E402


class ProjectViabilityCalculator(_BaseCalculator):
    """Calculadora de viabilidad — pure logic in ui.calculator, excel methods here."""

    def __init__(self, excel_manager: ExcelSharePointManager):
        self.excel = excel_manager

    def create_project(self, project_data: dict) -> tuple:
        """Crea nuevo proyecto"""
        results = self.calculate_viability(project_data)
        complete_project_data = {**project_data, **results}
        project_id = self.excel.add_project(complete_project_data)
        return project_id, results

    def update_project(self, project_id: str, project_data: dict) -> tuple:
        """Actualiza proyecto existente"""
        results = self.calculate_viability(project_data)
        complete_project_data = {**project_data, **results}

        if self.excel.update_project(project_id, complete_project_data):
            return project_id, results
        else:
            raise ValueError(f"No se pudo actualizar el proyecto {project_id}")

    def add_tracking(self, project_id: str, tracking_data: dict) -> tuple:
        """Añade seguimiento"""
        project_data = self.excel.get_project(project_id)
        if not project_data:
            raise ValueError(f"Proyecto {project_id} no encontrado")

        tracking_results = self.calculate_tracking_results(project_data, tracking_data)
        complete_tracking_data = {"project_id": project_id, **tracking_data, **tracking_results}

        # Guardar seguimiento
        tracking_id = self.excel.add_tracking(complete_tracking_data)

        # Actualizar proyecto con datos reales
        self.excel.update_project_from_tracking(project_id, tracking_results)

        return tracking_id, tracking_results


# =============================================================================
# FUNCIONES COMPARTIDAS PARA SIDEBAR
# =============================================================================


def render_language_selector():
    """Renderiza el selector de idioma en sidebar"""
    st.sidebar.markdown("---")

    language_options = ["🇪🇸 Español", "🇧🇷 Português"]
    current_lang = "🇪🇸 Español" if get_language() == "es" else "🇧🇷 Português"

    selected_language = st.sidebar.selectbox(
        t("language_label"), language_options, index=language_options.index(current_lang)
    )

    # Actualizar idioma si cambió
    new_lang = "es" if "🇪🇸" in selected_language else "pt"
    if st.session_state.language != new_lang:
        st.session_state.language = new_lang
        st.rerun()


def render_file_management():
    """Renderiza la gestión de archivos"""
    st.sidebar.header(t("file_management"))

    # Subir archivo existente
    uploaded_file = st.sidebar.file_uploader(t("upload_excel"), type=["xlsx"], help=t("upload_help"))

    if uploaded_file is not None:
        if st.sidebar.button(t("load_data_btn")):
            if st.session_state.excel_manager.load_from_uploaded_file(uploaded_file):
                st.sidebar.success(t("data_loaded"))
                st.rerun()

    # Descargar archivo actual
    if st.sidebar.button(t("generate_excel_btn")):
        buffer = st.session_state.excel_manager.upload_to_sharepoint_manual()

        st.sidebar.download_button(
            label=t("download_excel_btn"),
            data=buffer,
            file_name=f"project_viability_{datetime.now().strftime('%Y%m%d_%H%M')}.xlsx",
            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        )

        st.sidebar.info(t("sharepoint_steps"))

    # Guardar local
    if st.sidebar.button(t("save_local_btn")):
        if st.session_state.excel_manager.save_to_local_excel():
            st.sidebar.success(t("saved_local"))


def render_project_search():
    """Renderiza buscador de proyectos"""
    st.sidebar.header(t("search_projects"))

    search_term = st.sidebar.text_input(
        t("search_projects"), placeholder=t("search_placeholder"), label_visibility="collapsed"
    )

    if search_term:
        found_projects = st.session_state.excel_manager.search_projects(search_term)

        if found_projects:
            st.sidebar.success(f"✅ {len(found_projects)} {t('projects_found')}")

            # Mostrar proyectos encontrados
            for project in found_projects:
                with st.sidebar.expander(f"📋 {project['name']} ({project['id']})"):
                    st.write(f"**{t('priority')}:** {project['priority']}")
                    st.write(f"**Score:** {project['viability_score']}/100")
                    st.write(f"**{t('status')}:** {project['status']}")
                    st.write(f"**ROI:** {project['roi_first_year']:.1f}%")

                    if st.button(f"{t('edit_btn')} {project['id']}", key=f"edit_{project['id']}"):
                        st.session_state.selected_project_id = project["id"]
                        st.session_state.edit_mode = True
                        st.rerun()
        else:
            st.sidebar.warning(t("no_projects_found"))


def render_sidebar_stats():
    """Renderiza estadísticas en sidebar"""
    with st.sidebar:
        st.header(t("statistics"))
        projects = st.session_state.excel_manager.get_all_projects()
        trackings = st.session_state.excel_manager.tracking_df

        col_stats1, col_stats2 = st.columns(2)
        with col_stats1:
            st.metric(t("total_projects"), len(projects))
            if projects:
                high_priority = len([p for p in projects if p["priority"] == t("priority_high")])
                st.metric(t("high_priority"), high_priority)

        with col_stats2:
            if projects:
                executing = len(
                    [p for p in projects if str(p.get("status", "")).lower() in ("executing", "in_execution")]
                )
                st.metric(t("executing"), executing)

                implemented = len([p for p in projects if p["status"] == "implemented"])
                st.metric(t("implemented"), implemented)

        st.metric(t("total_trackings"), len(trackings))


def init_excel_manager():
    """Inicializa el gestor de Excel"""
    if "excel_manager" not in st.session_state:
        st.session_state.excel_manager = ExcelSharePointManager("")
        st.session_state.calculator = ProjectViabilityCalculator(st.session_state.excel_manager)
