# tracking.py
"""
MÃ³dulo de seguimiento post-implementaciÃ³n con procesamiento automÃ¡tico de encuestas
"""

import streamlit as st
import plotly.graph_objects as go
import pandas as pd
import os
from ui.tabs.shared import t
from ui.tabs.feedback_processor import FeedbackProcessor

def auto_process_feedback():
    """Procesa automÃ¡ticamente el archivo de encuesta en la misma carpeta"""
    try:
        # Nombre fijo del archivo de encuesta
        feedback_file = "encuesta_feedback.xlsx"  # Cambia este nombre si es diferente
        
        if not os.path.exists(feedback_file):
            return None, f"{t('tracking_feedback_file_not_found')} {feedback_file}"
        
        # Verificar que tiene las columnas correctas
        try:
            df = pd.read_excel(feedback_file)
            required_cols = ['ID DEL PROYECTO', 'Â¿QuÃ© tan satisfecho/a estÃ¡s con la nueva herramienta?']
            if not all(col in df.columns for col in required_cols):
                return None, f"{t('tracking_feedback_missing_columns')} {feedback_file}"
        except Exception as e:
            return None, f"{t('tracking_feedback_read_error')} {feedback_file}: {str(e)}"
        
        # Procesar archivo
        processor = FeedbackProcessor(
            st.session_state.excel_manager,
            st.session_state.calculator
        )
        
        results = processor.process_feedback_file(feedback_file)
        
        if results['success'] and results['processed_projects']:
            return results['processed_projects'], f"{t('tracking_feedback_processed_ok')} {results['processed_responses']} - {feedback_file}"
        elif results['processed_responses'] == 0:
            return None, f"{t('tracking_feedback_no_new')} {feedback_file}"
        else:
            errors = " | ".join(results['errors']) if results['errors'] else t("tracking_unknown_error")
            return None, f"{t('tracking_feedback_process_error')} {feedback_file}: {errors}"
            
    except Exception as e:
        return None, f"{t('tracking_auto_process_error')}: {str(e)}"

def get_tracking_source(project_id):
    """Determina si el tracking es manual o automÃ¡tico (de encuesta)"""
    trackings = st.session_state.excel_manager.get_project_tracking(project_id)
    if not trackings:
        return t("tracking_source_no_tracking"), ""
    
    latest = trackings[-1]
    
    # Si tiene datos tÃ­picos de encuesta automÃ¡tica
    has_satisfaction = latest.get('user_satisfaction_score', 0) > 0
    has_feedback_text = bool(
        latest.get('unexpected_benefits', '').strip() or 
        latest.get('challenges_faced', '').strip()
    )
    
    # Si tiene satisfacciÃ³n > 0 Y textos de feedback, probablemente es automÃ¡tico
    if has_satisfaction and has_feedback_text:
        return t("tracking_source_auto_survey"), "success"
    elif has_satisfaction or latest.get('actual_time_per_task', 0) > 0:
        return t("tracking_source_manual"), "info" 
    else:
        return t("tracking_source_no_data"), "warning"

def render_tracking_tab():
    """Renderiza tab de seguimiento con procesamiento automÃ¡tico"""
    st.header(t('tracking_tab'))
    
    # Procesamiento automÃ¡tico al inicio
    with st.spinner(t("tracking_spinner_search_feedback")):
        processed_projects, message = auto_process_feedback()
    
    # Mostrar resultado del procesamiento automÃ¡tico
    if processed_projects:
        st.success(message)
        
        # Mostrar detalles de proyectos actualizados
        with st.expander(f"{t('tracking_updated_projects_expander')}: {len(processed_projects)}"):
            for project in processed_projects:
                col1, col2, col3 = st.columns(3)
                with col1:
                    st.write(f"**ID:** {project['project_id']}")
                with col2:
                    st.write(f"**{t('tracking_satisfaction_label')}:** {project['satisfaction']}/10")
                with col3:
                    st.write(f"**{t('tracking_time_saved_label')}:** {project['time_reduction']:.1f}%")
    elif message:
        st.info(message)
    
    projects = [
        p
        for p in st.session_state.excel_manager.get_all_projects()
        if str(p.get("status", "")).lower() == "implemented"
    ]
    
    if not projects:
        st.warning(t('tracking_no_implemented_warning'))
        return
    
    # Agregar informaciÃ³n de fuente en el selector
    project_options = {}
    for p in projects:
        source, _ = get_tracking_source(p['id'])
        project_options[f"{p['name']} ({source}) - ID: {p['id']}"] = p['id']
    
    selected_project_name = st.selectbox(t('select_project'), list(project_options.keys()))
    selected_project_id = project_options[selected_project_name]
    
    project = st.session_state.excel_manager.get_project(selected_project_id)
    source, source_type = get_tracking_source(selected_project_id)
    
    # Mostrar estado del tracking
    if source_type == "success":
        st.success(f"{t('tracking_status_prefix')}: {source}")
    elif source_type == "info":
        st.info(f"{t('tracking_status_prefix')}: {source}")
    else:
        st.warning(f"{t('tracking_status_prefix')}: {source}")
    
    col1, col2 = st.columns([1, 1])
    
    with col1:
        st.subheader(t('tracking_data'))
        
        # Nota sobre el tipo de actualizaciÃ³n
        if source_type == "success":
            st.info(t("tracking_auto_data_info"))
        else:
            st.info(t("tracking_manual_or_wait_info"))
        
        months_tracked = st.number_input(t('months_tracked'), min_value=1, value=3)
        
        col1_1, col1_2 = st.columns(2)
        with col1_1:
            actual_time_per_task = st.number_input(
                t('actual_time_task'), 
                min_value=0.0, 
                value=0.0, 
                step=0.1
            )
            st.caption(f"{t('before_label')}: {project['current_time_per_task']} hrs")
        
        with col1_2:
            actual_tasks_per_month = st.number_input(
                t('actual_tasks_month'), 
                min_value=0, 
                value=int(project['tasks_per_month'])
            )
            st.caption(f"{t('projected_label')}: {project['tasks_per_month']}")
        
        st.subheader(t('adoption_satisfaction'))
        
        adoption_rate = st.slider(t('adoption_rate'), 0, 100, 80)
        st.caption(t('adoption_help'))
        
        user_satisfaction_score = st.slider(t('user_satisfaction'), 1, 10, 8)
        st.caption(t('satisfaction_help'))
        
        unexpected_benefits = st.text_area(
            t('unexpected_benefits'), 
            height=80,
            placeholder=t('unexpected_benefits_placeholder')
        )
        
        challenges_faced = st.text_area(
            t('challenges_faced'), 
            height=80,
            placeholder=t('challenges_placeholder')
        )
        
        lessons_learned = st.text_area(
            t('lessons_learned'), 
            height=80,
            placeholder=t('lessons_placeholder')
        )
        
        # BotÃ³n con texto dinÃ¡mico
        button_text = t("tracking_update_btn") if source_type == "success" else t('save_tracking_btn')
        
        if st.button(button_text, type="primary"):
            tracking_data = {
                'months_tracked': months_tracked,
                'actual_time_per_task': actual_time_per_task,
                'actual_tasks_per_month': actual_tasks_per_month,
                'adoption_rate': adoption_rate,
                'user_satisfaction_score': user_satisfaction_score,
                'unexpected_benefits': unexpected_benefits,
                'challenges_faced': challenges_faced,
                'lessons_learned': lessons_learned
            }
            
            try:
                tracking_id, results = st.session_state.calculator.add_tracking(selected_project_id, tracking_data)
                if source_type == "success":
                    st.success(f"{t('tracking_updated_manual')}: {tracking_id}")
                else:
                    st.success(f"{t('tracking_saved')}: {tracking_id}")
                st.rerun()
            except Exception as e:
                st.error(f"{t('error_occurred')}: {str(e)}")
    
    with col2:
        trackings = st.session_state.excel_manager.get_project_tracking(selected_project_id)
        
        if trackings:
            latest = trackings[-1]
            
            st.subheader(f"ðŸ“ˆ {t('real_performance')}")
            
            # Indicador de fuente de datos
            if source_type == "success":
                st.success(t("tracking_auto_source"))
            elif source_type == "info":
                st.info(t("tracking_manual_source"))
            
            # Performance gauge
            fig_perf = go.Figure(go.Indicator(
                mode = "gauge+number",
                value = latest['performance_score'],
                title = {'text': t('real_performance')},
                gauge = {
                    'axis': {'range': [None, 100]},
                    'bar': {'color': 'darkblue'},
                    'steps': [
                        {'range': [0, 40], 'color': "lightcoral"},
                        {'range': [40, 60], 'color': "yellow"},
                        {'range': [60, 80], 'color': "lightgreen"},
                        {'range': [80, 100], 'color': "green"}
                    ]
                }
            ))
            fig_perf.update_layout(height=250)
            st.plotly_chart(fig_perf, use_container_width=True)
            
            # Mensaje de interpretaciÃ³n
            performance = latest['performance_score']
            if performance >= 80:
                st.success(t('excellent_performance'))
            elif performance >= 60:
                st.info(t('good_performance'))
            elif performance >= 40:
                st.warning(t('moderate_performance'))
            else:
                st.error(t('low_performance'))
            
            # MÃ©tricas principales
            col2_1, col2_2 = st.columns(2)
            with col2_1:
                st.metric(t("tracking_efficiency_label"), f"{latest['efficiency_ratio']}x")
                st.metric(t('adoption_rate'), f"{latest['adoption_rate']:.0f}%")
            
            with col2_2:
                st.metric(t('real_savings_month'), f"${latest['actual_monthly_savings']:,.0f}")
                st.metric(t('user_satisfaction'), f"{latest['user_satisfaction_score']:.1f}/10")
            
            # ComparaciÃ³n esperado vs real
            st.subheader(t('expected_vs_real'))
            
            expected_monthly_savings = (project['current_time_per_task'] * 
                                      project['time_reduction_percent'] / 100 * 
                                      project['tasks_per_month'] * 
                                      project['staff_count'] * 
                                      project['avg_salary_per_hour'])
            
            col2_3, col2_4 = st.columns(2)
            with col2_3:
                st.metric(t('expected_reduction'), f"{project['time_reduction_percent']}%")
                st.metric(t('expected_savings_month'), f"${expected_monthly_savings:,.0f}")
            
            with col2_4:
                st.metric(t('real_reduction'), f"{latest['actual_time_reduction_percent']}%")
                st.metric(t('real_savings_month'), f"${latest['actual_monthly_savings']:,.0f}")
            
            # Eficiencia del proyecto con interpretaciÃ³n
            efficiency = latest['efficiency_ratio']
            if efficiency >= 1.2:
                efficiency_text = t('exceeded_significantly')
                efficiency_color = "ðŸŸ¢"
            elif efficiency >= 1:
                efficiency_text = t('met_expectations')
                efficiency_color = "ðŸ”µ"
            elif efficiency >= 0.7:
                efficiency_text = t('close_expectations')
                efficiency_color = "ðŸŸ¡"
            else:
                efficiency_text = t('below_expectations')
                efficiency_color = "ðŸ”´"
            
            st.metric(
                f"{efficiency_color} {t('project_efficiency')}", 
                f"{efficiency}x",
                help=efficiency_text
            )
            
            # AnÃ¡lisis cualitativo si existe
            if any([latest.get('unexpected_benefits'), latest.get('challenges_faced'), latest.get('lessons_learned')]):
                st.subheader(t("tracking_qualitative_analysis"))
                
                if latest.get('unexpected_benefits'):
                    with st.expander(t("tracking_unexpected_benefits_expander")):
                        st.write(latest['unexpected_benefits'])
                
                if latest.get('challenges_faced'):
                    with st.expander(t("tracking_challenges_expander")):
                        st.write(latest['challenges_faced'])
                
                if latest.get('lessons_learned'):
                    with st.expander(t("tracking_lessons_expander")):
                        st.write(latest['lessons_learned'])
            
            # Recomendaciones basadas en performance
            st.subheader(t("tracking_recommendations"))
            
            recommendations = []
            
            if efficiency >= 1.2:
                recommendations.append(t("tracking_reco_replicate"))
            
            if efficiency < 0.8:
                recommendations.append(t("tracking_reco_review_method"))
            
            if latest['adoption_rate'] < 70:
                recommendations.append(t("tracking_reco_change_training"))
            
            if latest['user_satisfaction_score'] < 7:
                recommendations.append(t("tracking_reco_involve_users"))
            
            if performance >= 90:
                recommendations.append(t("tracking_reco_expand_scope"))
            
            if recommendations:
                for rec in recommendations:
                    st.info(rec)
            else:
                st.success(t("tracking_project_on_track"))
        
        else:
            st.info(t("tracking_no_tracking_for_project"))
            
            # Mostrar informaciÃ³n del proyecto seleccionado
            st.subheader(t("tracking_project_info_title"))
            st.write(f"**{t('project_name')}:** {project['name']}")
            st.write(f"**Score de Viabilidad:** {project['viability_score']}/100")
            st.write(f"**{t('priority')}:** {project['priority']}")
            st.write(f"**ReducciÃ³n Esperada:** {project['time_reduction_percent']}%")
            st.write(f"**{t('monthly_savings')} Proyectado:** ${project['monthly_savings']:,.0f}")
            
            if source_type == "warning":
                st.info(t("tracking_auto_when_feedback"))
            else:
                st.info(t("tracking_fill_form_hint"))# tracking.py
"""
MÃ³dulo de seguimiento post-implementaciÃ³n
"""

import streamlit as st
import plotly.graph_objects as go
from ui.tabs.shared import t

def render_tracking_tab():
    """Renderiza tab de seguimiento"""
    st.header(t('tracking_tab'))
    
    projects = [
        p
        for p in st.session_state.excel_manager.get_all_projects()
        if str(p.get("status", "")).lower() == "implemented"
    ]
    
    if not projects:
        st.warning(t('tracking_no_implemented_warning'))
        return
    
    project_options = {f"{p['name']} (ID: {p['id']})": p['id'] for p in projects}
    selected_project_name = st.selectbox(t('select_project'), list(project_options.keys()))
    selected_project_id = project_options[selected_project_name]
    
    project = st.session_state.excel_manager.get_project(selected_project_id)
    
    col1, col2 = st.columns([1, 1])
    
    with col1:
        st.subheader(t('tracking_data'))
        
        months_tracked = st.number_input(t('months_tracked'), min_value=1, value=3)
        
        col1_1, col1_2 = st.columns(2)
        with col1_1:
            actual_time_per_task = st.number_input(
                t('actual_time_task'), 
                min_value=0.0, 
                value=0.0, 
                step=0.1
            )
            st.caption(f"{t('before_label')}: {project['current_time_per_task']} hrs")
        
        with col1_2:
            actual_tasks_per_month = st.number_input(
                t('actual_tasks_month'), 
                min_value=0, 
                value=int(project['tasks_per_month'])
            )
            st.caption(f"{t('projected_label')}: {project['tasks_per_month']}")
        
        st.subheader(t('adoption_satisfaction'))
        
        adoption_rate = st.slider(t('adoption_rate'), 0, 100, 80)
        st.caption(t('adoption_help'))
        
        user_satisfaction_score = st.slider(t('user_satisfaction'), 1, 10, 8)
        st.caption(t('satisfaction_help'))
        
        unexpected_benefits = st.text_area(
            t('unexpected_benefits'), 
            height=80,
            placeholder=t('unexpected_benefits_placeholder')
        )
        
        challenges_faced = st.text_area(
            t('challenges_faced'), 
            height=80,
            placeholder=t('challenges_placeholder')
        )
        
        lessons_learned = st.text_area(
            t('lessons_learned'), 
            height=80,
            placeholder=t('lessons_placeholder')
        )
        
        if st.button(t('save_tracking_btn'), type="primary"):
            tracking_data = {
                'months_tracked': months_tracked,
                'actual_time_per_task': actual_time_per_task,
                'actual_tasks_per_month': actual_tasks_per_month,
                'adoption_rate': adoption_rate,
                'user_satisfaction_score': user_satisfaction_score,
                'unexpected_benefits': unexpected_benefits,
                'challenges_faced': challenges_faced,
                'lessons_learned': lessons_learned
            }
            
            try:
                tracking_id, results = st.session_state.calculator.add_tracking(selected_project_id, tracking_data)
                st.success(f"{t('tracking_saved')}: {tracking_id}")
                st.rerun()
            except Exception as e:
                st.error(f"{t('error_occurred')}: {str(e)}")
    
    with col2:
        trackings = st.session_state.excel_manager.get_project_tracking(selected_project_id)
        
        if trackings:
            latest = trackings[-1]
            
            st.subheader(f"ðŸ“ˆ {t('real_performance')}")
            
            # Performance gauge
            fig_perf = go.Figure(go.Indicator(
                mode = "gauge+number",
                value = latest['performance_score'],
                title = {'text': t('real_performance')},
                gauge = {
                    'axis': {'range': [None, 100]},
                    'bar': {'color': 'darkblue'},
                    'steps': [
                        {'range': [0, 40], 'color': "lightcoral"},
                        {'range': [40, 60], 'color': "yellow"},
                        {'range': [60, 80], 'color': "lightgreen"},
                        {'range': [80, 100], 'color': "green"}
                    ]
                }
            ))
            fig_perf.update_layout(height=250)
            st.plotly_chart(fig_perf, use_container_width=True)
            
            # Mensaje de interpretaciÃ³n
            performance = latest['performance_score']
            if performance >= 80:
                st.success(t('excellent_performance'))
            elif performance >= 60:
                st.info(t('good_performance'))
            elif performance >= 40:
                st.warning(t('moderate_performance'))
            else:
                st.error(t('low_performance'))
            
            # MÃ©tricas principales
            col2_1, col2_2 = st.columns(2)
            with col2_1:
                st.metric(t("tracking_efficiency_label"), f"{latest['efficiency_ratio']}x")
                st.metric(t('adoption_rate'), f"{latest['adoption_rate']:.0f}%")
            
            with col2_2:
                st.metric(t('real_savings_month'), f"${latest['actual_monthly_savings']:,.0f}")
                st.metric(t('user_satisfaction'), f"{latest['user_satisfaction_score']:.1f}/10")
            
            # ComparaciÃ³n esperado vs real
            st.subheader(t('expected_vs_real'))
            
            expected_monthly_savings = (project['current_time_per_task'] * 
                                      project['time_reduction_percent'] / 100 * 
                                      project['tasks_per_month'] * 
                                      project['staff_count'] * 
                                      project['avg_salary_per_hour'])
            
            col2_3, col2_4 = st.columns(2)
            with col2_3:
                st.metric(t('expected_reduction'), f"{project['time_reduction_percent']}%")
                st.metric(t('expected_savings_month'), f"${expected_monthly_savings:,.0f}")
            
            with col2_4:
                st.metric(t('real_reduction'), f"{latest['actual_time_reduction_percent']}%")
                st.metric(t('real_savings_month'), f"${latest['actual_monthly_savings']:,.0f}")
            
            # Eficiencia del proyecto con interpretaciÃ³n
            efficiency = latest['efficiency_ratio']
            if efficiency >= 1.2:
                efficiency_text = t('exceeded_significantly')
                efficiency_color = "ðŸŸ¢"
            elif efficiency >= 1:
                efficiency_text = t('met_expectations')
                efficiency_color = "ðŸ”µ"
            elif efficiency >= 0.7:
                efficiency_text = t('close_expectations')
                efficiency_color = "ðŸŸ¡"
            else:
                efficiency_text = t('below_expectations')
                efficiency_color = "ðŸ”´"
            
            st.metric(
                f"{efficiency_color} {t('project_efficiency')}", 
                f"{efficiency}x",
                help=efficiency_text
            )
            
            # AnÃ¡lisis cualitativo si existe
            if any([latest.get('unexpected_benefits'), latest.get('challenges_faced'), latest.get('lessons_learned')]):
                st.subheader(t("tracking_qualitative_analysis"))
                
                if latest.get('unexpected_benefits'):
                    with st.expander(t("tracking_unexpected_benefits_expander")):
                        st.write(latest['unexpected_benefits'])
                
                if latest.get('challenges_faced'):
                    with st.expander(t("tracking_challenges_expander")):
                        st.write(latest['challenges_faced'])
                
                if latest.get('lessons_learned'):
                    with st.expander(t("tracking_lessons_expander")):
                        st.write(latest['lessons_learned'])
            
            # Recomendaciones basadas en performance
            st.subheader(t("tracking_recommendations"))
            
            recommendations = []
            
            if efficiency >= 1.2:
                recommendations.append(t("tracking_reco_replicate"))
            
            if efficiency < 0.8:
                recommendations.append(t("tracking_reco_review_method"))
            
            if latest['adoption_rate'] < 70:
                recommendations.append(t("tracking_reco_change_training"))
            
            if latest['user_satisfaction_score'] < 7:
                recommendations.append(t("tracking_reco_involve_users"))
            
            if performance >= 90:
                recommendations.append(t("tracking_reco_expand_scope"))
            
            if recommendations:
                for rec in recommendations:
                    st.info(rec)
            else:
                st.success(t("tracking_project_on_track"))
        
        else:
            st.info(t("tracking_no_tracking_for_project"))
            
            # Mostrar informaciÃ³n del proyecto seleccionado
            st.subheader(t("tracking_project_info_title"))
            st.write(f"**{t('project_name')}:** {project['name']}")
            st.write(f"**Score de Viabilidad:** {project['viability_score']}/100")
            st.write(f"**{t('priority')}:** {project['priority']}")
            st.write(f"**ReducciÃ³n Esperada:** {project['time_reduction_percent']}%")
            st.write(f"**{t('monthly_savings')} Proyectado:** ${project['monthly_savings']:,.0f}")

            st.info(t("tracking_fill_form_hint"))

