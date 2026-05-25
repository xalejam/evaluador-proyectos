# planning.py
"""
Módulo de planificación de proyectos con botones separados de Calcular y Guardar
"""

import json

import plotly.graph_objects as go
import streamlit as st

from infra.config_loader import ConfigLoader
from infra.config_loader import load_app_config as _load_app_config
from infra.db.adapter import PLACEHOLDER, db_now, db_table_columns
from infra.db.connection import get_sqlite_conn as get_conn
from infra.db.migrations import ensure_evaluations_schema, ensure_projects_schema
from infra.folder_provisioner import load_provisioner_from_config
from infra.integrations.use_case_matrix_sync import (
    sync_to_use_case_matrix,
)
from ui.i18n_labels import get_lang, help_statuses, label_status
from ui.tabs.shared import get_scale_salary, t


def _safe_float(value, default: float = 0.0) -> float:
    """Convierte un valor a float de forma segura."""
    if value is None or value == "":
        return default
    try:
        return float(value)
    except (ValueError, TypeError):
        return default


def _safe_int(value, default: int = 0) -> int:
    """Convierte un valor a int de forma segura."""
    if value is None or value == "":
        return default
    try:
        return int(float(value))
    except (ValueError, TypeError):
        return default


def calculate_average_hourly_rate():
    """Calcula la hora promedio de todos los proyectos en el Excel"""
    try:
        projects = st.session_state.excel_manager.get_all_projects()
        if not projects:
            return 25.0  # Valor por defecto si no hay proyectos

        total_rate = sum(p.get("avg_salary_per_hour", 25) for p in projects)
        avg_rate = total_rate / len(projects)
        return round(avg_rate, 2)
    except Exception:
        return 25.0  # Valor por defecto en caso de error


EVALUATION_SAVE_STATUSES = ("evaluated", "backlog", "on_hold", "rejected", "handed_off")
_app_config = _load_app_config()
DEVELOPER_TEAMS = tuple(_app_config.get("delivery_teams", []))


def _impact_points(time_reduction: float) -> float:
    if time_reduction >= 70:
        return 35.0
    if time_reduction >= 50:
        return 30.0
    if time_reduction >= 30:
        return 25.0
    if time_reduction >= 15:
        return 20.0
    if time_reduction >= 5:
        return 15.0
    return max(0.0, time_reduction * 0.5)


def _risk_points(risk_level: int) -> float:
    return {1: 30.0, 2: 24.0, 3: 18.0, 4: 12.0, 5: 6.0}.get(int(risk_level), 6.0)


def _complexity_points(complexity_level: int) -> float:
    return {1: 35.0, 2: 28.0, 3: 21.0, 4: 14.0, 5: 7.0}.get(int(complexity_level), 7.0)


def _build_project_payload(
    project_name: str,
    project_description: str,
    project_country: str,
    project_owner: str,
    current_time_per_task: float,
    tasks_per_month: int,
    staff_count: int,
    avg_hourly_rate: float,
    time_reduction_percent: int,
    development_hours: int,
    development_cost_per_hour: float,
    maintenance_monthly: float,
    complexity_value: int,
    risk_value: int,
) -> dict:
    return {
        "name": project_name,
        "description": project_description,
        "country": project_country,
        "owner": project_owner,
        "current_time_per_task": current_time_per_task,
        "tasks_per_month": tasks_per_month,
        "staff_count": staff_count,
        "avg_salary_per_hour": avg_hourly_rate,
        "time_reduction_percent": time_reduction_percent,
        "development_hours": development_hours,
        "development_cost_per_hour": development_cost_per_hour,
        "maintenance_monthly": maintenance_monthly,
        "implementation_complexity": complexity_value,
        "risk_level": risk_value,
    }


def insert_project_evaluation_snapshot(
    conn,
    project_id: str,
    action: str,
    status_after: str,
    calc_results: dict,
    inputs_dict: dict,
    author: str,
) -> None:
    impact_score = _impact_points(_safe_float(inputs_dict.get("time_reduction_percent")))
    risk_score = _risk_points(_safe_int(inputs_dict.get("risk_level"), 3))
    complexity_score = _complexity_points(_safe_int(inputs_dict.get("implementation_complexity"), 3))

    conn.execute(
        f"""
        INSERT INTO project_evaluations (
            project_id, created_by, action, status_after,
            score_total, score_impact, score_risk, score_complexity,
            monthly_savings, annual_savings, payback_period_months, roi_first_year,
            hours_saved_per_month, inputs_json
        ) VALUES ({", ".join([PLACEHOLDER] * 14)})
        """,
        (
            project_id,
            (author or "").strip(),
            action,
            status_after,
            _safe_float(calc_results.get("viability_score")),
            impact_score,
            risk_score,
            complexity_score,
            _safe_float(calc_results.get("monthly_savings")),
            _safe_float(calc_results.get("annual_savings")),
            calc_results.get("payback_period_months"),
            _safe_float(calc_results.get("roi_first_year")),
            _safe_float(calc_results.get("hours_saved_per_month")),
            json.dumps(inputs_dict, ensure_ascii=False),
        ),
    )
    conn.commit()


def save_project(
    conn, payload: dict, status_after: str, loop_url_optional: str | None = None, developer_team: str = ""
) -> tuple:
    """
    Persiste proyecto en projects con create/update y deja estado final.
    Retorna (project_id, calc_results, created_new).
    """
    manager = st.session_state.excel_manager
    calculator = st.session_state.calculator

    existing_id = st.session_state.get("selected_project_id")
    created_new = not bool(existing_id and manager.project_exists(existing_id))

    if created_new:
        project_id, calc_results = calculator.create_project(payload)
    else:
        project_id, calc_results = calculator.update_project(existing_id, payload)

    projects_cols = db_table_columns(conn, "projects")
    updates = {"status": status_after, "project_id": project_id}

    if "loop_url" in projects_cols and loop_url_optional is not None:
        updates["loop_url"] = loop_url_optional.strip()
    if "developer_team" in projects_cols:
        updates["developer_team"] = (developer_team or "").strip()

    set_parts = [f"updated_at = {PLACEHOLDER}"]
    params = [db_now()]
    for key, val in updates.items():
        if key in projects_cols:
            set_parts.append(f"{key} = {PLACEHOLDER}")
            params.append(val)

    if set_parts:
        params.append(project_id)
        conn.execute(f"UPDATE projects SET {', '.join(set_parts)} WHERE id = {PLACEHOLDER}", params)
        conn.commit()

    return project_id, calc_results, created_new


def render_planning_tab_old():
    """Compat legacy: delega al render actual de viabilidad."""
    return render_planning_tab()


def render_planning_tab():
    """Renderiza tab de viabilidad (v2 con acciones separadas)."""
    st.header(t("viability_tab"))

    # Migraciones idempotentes al abrir pestaña
    with get_conn() as conn:
        ensure_projects_schema(conn)
        ensure_evaluations_schema(conn)

    config = ConfigLoader().load()
    default_countries = ["MX", "BR", "CO", "AR", "CL", "PE", "EC", "UY", "BO", "NOLA", "HISPANIC", "LATAM"]
    configured_countries = config.get("countries", [])
    if configured_countries:
        # Mantiene lo definido en config y agrega faltantes de la lista base sin duplicar.
        countries = list(dict.fromkeys(list(configured_countries) + default_countries))
    else:
        countries = default_countries
    avg_hourly_rate = calculate_average_hourly_rate()

    edit_mode = getattr(st.session_state, "edit_mode", False)
    selected_project = None
    if edit_mode and st.session_state.get("selected_project_id"):
        selected_project = st.session_state.excel_manager.get_project(st.session_state.selected_project_id)
        if not selected_project:
            st.error(t("project_not_found"))
            st.session_state.edit_mode = False

    temp_calc = st.session_state.get("temp_calculation")
    current_project_id = st.session_state.get("selected_project_id")
    current_status = (selected_project or {}).get("status", "nuevo")
    current_score = None
    if temp_calc and temp_calc.get("results"):
        current_score = temp_calc["results"].get("viability_score")
    elif selected_project:
        current_score = selected_project.get("viability_score")

    bar1, bar2, bar3, bar4 = st.columns([2, 1, 1, 2])
    with bar1:
        st.caption(t("project_label"))
        st.write(current_project_id or t("project_id_pending"))
    with bar2:
        st.caption(t("status"))
        st.write(current_status or t("na"))
    with bar3:
        st.caption(t("current_score"))
        st.write(f"{int(current_score)}/100" if current_score is not None else t("na"))
    with bar4:
        st.caption(t("loop_label"))
        loop_url_bar = (selected_project or {}).get("loop_url", "")
        if loop_url_bar:
            st.link_button(t("open_loop_btn"), loop_url_bar)
        else:
            st.write(t("no_link"))

    col1, col2 = st.columns([1, 1])

    with col1:
        mode1, mode2, mode3 = st.columns(3)
        with mode1:
            if st.button(t("new_project_btn"), type="secondary"):
                st.session_state.edit_mode = False
                st.session_state.selected_project_id = None
                st.session_state.temp_calculation = None
                st.rerun()
        with mode2:
            if st.button(t("search_edit_btn"), type="secondary"):
                st.session_state.edit_mode = True
                st.rerun()
        with mode3:
            if edit_mode and st.button(t("cancel_btn"), type="secondary"):
                st.session_state.edit_mode = False
                st.session_state.selected_project_id = None
                st.session_state.temp_calculation = None
                st.rerun()

        if edit_mode:
            all_projects = st.session_state.excel_manager.get_all_projects()
            if not all_projects:
                st.warning(t("no_projects_found"))
            else:
                project_options = []
                project_map = {}
                for project in all_projects:
                    project_id = str(project.get("id", "")).strip()
                    if not project_id:
                        continue
                    project_name = str(project.get("name", "")).strip() or t("na")
                    option_label = f"{project_name} ({project_id})"
                    project_options.append(option_label)
                    project_map[option_label] = project_id

                if project_options:
                    current_selected_id = st.session_state.get("selected_project_id")
                    default_idx = 0
                    if current_selected_id:
                        for idx, label in enumerate(project_options):
                            if label.endswith(f"({current_selected_id})"):
                                default_idx = idx
                                break

                    selected_label = st.selectbox(
                        t("select_project"),
                        options=project_options,
                        index=default_idx,
                        key="planning_edit_project_selector",
                    )
                    if st.button(t("edit_btn"), key="planning_load_project_btn"):
                        st.session_state.selected_project_id = project_map[selected_label]
                        st.session_state.temp_calculation = None
                        st.rerun()

        st.subheader(t("evaluation_form"))
        project_name = st.text_input(
            t("project_name"),
            value=selected_project["name"] if selected_project else "",
            placeholder=t("project_name_placeholder"),
        )

        col_meta1, col_meta2 = st.columns(2)
        with col_meta1:
            current_country = selected_project.get("country", countries[0]) if selected_project else countries[0]
            country_index = countries.index(current_country) if current_country in countries else 0
            project_country = st.selectbox(t("country_iso2"), countries, index=country_index)
        with col_meta2:
            project_owner = (
                st.text_input(
                    t("owner_label"),
                    value=(selected_project.get("owner", "") if selected_project else ""),
                    help=t("owner_help"),
                )
                .strip()
                .upper()
            )

        st.subheader(t("current_situation"))
        c1, c2 = st.columns(2)
        with c1:
            current_time_per_task = st.number_input(
                t("time_per_task"),
                min_value=0.0,
                value=float(selected_project["current_time_per_task"]) if selected_project else 0.0,
                step=0.5,
            )
            staff_count = st.number_input(
                t("staff_count"),
                min_value=1,
                value=int(selected_project["staff_count"]) if selected_project else 1,
            )
        with c2:
            tasks_per_month = st.number_input(
                t("tasks_per_month"),
                min_value=0,
                value=int(selected_project["tasks_per_month"]) if selected_project else 0,
            )
            time_reduction_percent = st.slider(
                t("time_reduction"),
                0,
                100,
                int(selected_project["time_reduction_percent"]) if selected_project else 0,
                5,
            )

        st.caption(f"{t('financial_average_rate_caption')} ${avg_hourly_rate:.2f}/hr")

        with st.expander(t("optional_details"), expanded=False):
            project_description = st.text_area(
                t("project_description"),
                height=100,
                value=selected_project["description"] if selected_project else "",
                placeholder=t("project_description_placeholder"),
            )

            scale_options = list(t("scale_levels").values())
            current_salary = float(selected_project["avg_salary_per_hour"]) if selected_project else avg_hourly_rate
            current_scale_index = 6
            for i, (scale_key, _) in enumerate(t("scale_levels").items()):
                if scale_key != "Personalizado" and abs(get_scale_salary(scale_key) - current_salary) < 1:
                    current_scale_index = i
                    break
            st.selectbox(
                "Scale del personal (solo referencia)",
                scale_options,
                index=current_scale_index,
                help=t("scale_reference_help"),
            )

            dc1, dc2 = st.columns(2)
            with dc1:
                development_hours = st.number_input(
                    t("development_hours"),
                    min_value=0,
                    value=int(selected_project["development_hours"]) if selected_project else 0,
                )
            with dc2:
                dev_scale_options = list(t("scale_levels").values())
                current_dev_cost = float(selected_project["development_cost_per_hour"]) if selected_project else 50.0
                current_dev_scale_index = 6
                for i, (scale_key, _) in enumerate(t("scale_levels").items()):
                    if scale_key != "Personalizado" and abs(get_scale_salary(scale_key) - current_dev_cost) < 1:
                        current_dev_scale_index = i
                        break
                selected_dev_scale = st.selectbox(
                    t("dev_salary_scale"), dev_scale_options, index=current_dev_scale_index
                )
                if t("salary_custom") in selected_dev_scale:
                    development_cost_per_hour = st.number_input(
                        t("cost_per_hour"),
                        min_value=0.0,
                        value=current_dev_cost,
                        step=1.0,
                        key="dev_cost_custom_viab",
                    )
                else:
                    dev_scale_key = None
                    for key, label in t("scale_levels").items():
                        if label == selected_dev_scale:
                            dev_scale_key = key
                            break
                    development_cost_per_hour = get_scale_salary(dev_scale_key) if dev_scale_key else 50.0

            maintenance_monthly = st.number_input(
                t("monthly_maintenance"),
                min_value=0.0,
                value=float(selected_project["maintenance_monthly"]) if selected_project else 0.0,
            )

            risk_options = [t("risk_options")[i] for i in range(1, 6)]
            complexity_options = [t("complexity_options")[i] for i in range(1, 6)]
            implementation_complexity = st.selectbox(
                t("implementation_complexity"),
                complexity_options,
                index=(int(selected_project["implementation_complexity"]) - 1) if selected_project else 0,
            )
            risk_level = st.selectbox(
                t("technical_risk"),
                risk_options,
                index=(int(selected_project["risk_level"]) - 1) if selected_project else 0,
            )
            developer_team = st.selectbox(
                t("developer_team_label"),
                list(DEVELOPER_TEAMS),
                index=(
                    list(DEVELOPER_TEAMS).index(selected_project.get("developer_team"))
                    if selected_project and selected_project.get("developer_team") in DEVELOPER_TEAMS
                    else 0
                ),
            )

        development_hours = locals().get(
            "development_hours", int(selected_project["development_hours"]) if selected_project else 0
        )
        development_cost_per_hour = locals().get(
            "development_cost_per_hour",
            float(selected_project["development_cost_per_hour"]) if selected_project else 50.0,
        )
        maintenance_monthly = locals().get(
            "maintenance_monthly",
            float(selected_project["maintenance_monthly"]) if selected_project else 0.0,
        )
        implementation_complexity = locals().get(
            "implementation_complexity",
            (
                t("complexity_options")[int(selected_project["implementation_complexity"])]
                if selected_project
                else t("complexity_options")[1]
            ),
        )
        risk_level = locals().get(
            "risk_level",
            t("risk_options")[int(selected_project["risk_level"])] if selected_project else t("risk_options")[1],
        )
        developer_team = locals().get(
            "developer_team",
            selected_project.get("developer_team", DEVELOPER_TEAMS[0]) if selected_project else DEVELOPER_TEAMS[0],
        )
        project_description = locals().get(
            "project_description", selected_project["description"] if selected_project else ""
        )

        complexity_value = int(str(implementation_complexity).split(" - ")[0])
        risk_value = int(str(risk_level).split(" - ")[0])

        project_data = _build_project_payload(
            project_name=project_name,
            project_description=project_description,
            project_country=project_country,
            project_owner=project_owner,
            current_time_per_task=current_time_per_task,
            tasks_per_month=tasks_per_month,
            staff_count=staff_count,
            avg_hourly_rate=avg_hourly_rate,
            time_reduction_percent=time_reduction_percent,
            development_hours=development_hours,
            development_cost_per_hour=development_cost_per_hour,
            maintenance_monthly=maintenance_monthly,
            complexity_value=complexity_value,
            risk_value=risk_value,
        )

        st.markdown("---")
        current_lang = get_lang()
        visible_options = [label_status(s, current_lang) for s in EVALUATION_SAVE_STATUSES]
        reverse_mapping = {label: status for status, label in zip(EVALUATION_SAVE_STATUSES, visible_options)}
        selected_label = st.selectbox(
            t("save_evaluation_status_label"),
            options=visible_options,
            index=0,
            help=help_statuses(current_lang),
        )
        save_status = reverse_mapping[selected_label]
        author = st.text_input(
            t("action_owner_label"),
            value=str(st.session_state.get("author", st.session_state.get("current_user", "Xiomara Monroy"))),
        )

        b1, b2, b3 = st.columns(3)
        with b1:
            eval_click = st.button(t("evaluate_btn"), type="secondary", use_container_width=True)
        with b2:
            save_eval_click = st.button(t("save_evaluation_btn"), type="primary", use_container_width=True)
        with b3:
            approve_click = st.button(t("approve_to_agenda_btn"), type="primary", use_container_width=True)

        if eval_click:
            if not project_name:
                st.error(t("name_required"))
            elif not project_owner:
                st.error(t("owner_required"))
            else:
                results = st.session_state.calculator.calculate_viability(project_data)
                st.session_state.temp_calculation = {
                    "project_data": project_data,
                    "results": results,
                    "is_temporary": True,
                }
                st.success(t("evaluation_calculated_not_saved"))
                st.rerun()

        if save_eval_click or approve_click:
            if not project_name:
                st.error(t("name_required"))
            elif not project_owner:
                st.error(t("owner_required"))
            else:
                calc_bundle = st.session_state.get("temp_calculation")
                if calc_bundle and calc_bundle.get("project_data"):
                    calc_inputs = {**calc_bundle["project_data"], **project_data}
                    calc_results = st.session_state.calculator.calculate_viability(calc_inputs)
                else:
                    calc_inputs = project_data
                    calc_results = st.session_state.calculator.calculate_viability(calc_inputs)

                is_existing = bool(st.session_state.get("selected_project_id"))
                status_after = save_status
                action = "recalc_saved" if is_existing else "evaluation_saved"

                if approve_click:
                    current_project = (
                        st.session_state.excel_manager.get_project(st.session_state.get("selected_project_id"))
                        if is_existing
                        else None
                    )
                    current_state = (current_project or {}).get("status", "")
                    if current_state in ("executing", "implemented", "handed_off"):
                        status_after = current_state
                    else:
                        status_after = "approved"
                    action = "approved"

                try:
                    with get_conn() as conn:
                        project_id, persisted_results, _ = save_project(
                            conn=conn,
                            payload=calc_inputs,
                            status_after=status_after,
                            loop_url_optional=None,
                            developer_team=developer_team,
                        )
                        insert_project_evaluation_snapshot(
                            conn=conn,
                            project_id=project_id,
                            action=action,
                            status_after=status_after,
                            calc_results=persisted_results,
                            inputs_dict=calc_inputs,
                            author=author,
                        )

                    sync_to_use_case_matrix(project_id, calc_inputs, persisted_results)
                    st.session_state.selected_project_id = project_id
                    st.session_state.latest_results = persisted_results
                    st.session_state.temp_calculation = {
                        "project_data": calc_inputs,
                        "results": persisted_results,
                        "is_temporary": False,
                    }
                    msg = t("project_approved_sent_to_agenda") if approve_click else t("evaluation_saved_msg")
                    st.success(f"{msg} ID: {project_id}")

                    if approve_click:
                        try:
                            provisioner = load_provisioner_from_config()
                            prov_result = provisioner.provision(
                                project_id=project_id,
                                project_name=calc_inputs.get("name", ""),
                                description=calc_inputs.get("description", ""),
                            )
                            if prov_result.success:
                                st.info(
                                    t("folder_provisioned_ok").format(
                                        path=prov_result.folder_path,
                                        color=prov_result.color.value,
                                    )
                                )
                            else:
                                st.warning(t("folder_provisioned_warning").format(error=prov_result.error))
                        except Exception as prov_exc:
                            st.warning(t("folder_provisioned_warning").format(error=str(prov_exc)))

                    st.rerun()
                except Exception as exc:
                    st.error(f"{t('error_occurred')}: {exc}")

    with col2:
        project_to_show = None
        is_temporary = False
        if st.session_state.get("temp_calculation"):
            project_to_show = {
                **st.session_state.temp_calculation.get("project_data", {}),
                **st.session_state.temp_calculation.get("results", {}),
            }
            is_temporary = bool(st.session_state.temp_calculation.get("is_temporary", True))
        elif st.session_state.get("selected_project_id"):
            project_to_show = st.session_state.excel_manager.get_project(st.session_state.selected_project_id)

        if not project_to_show:
            st.info(t("evaluate_to_view_results_info"))
            return

        if is_temporary:
            st.warning(t("temporary_results_warning"))
        else:
            st.success(t("persisted_results_success"))

        viability_score = _safe_float(project_to_show.get("viability_score"))
        fig_gauge = go.Figure(
            go.Indicator(
                mode="gauge+number",
                value=viability_score,
                title={"text": t("viability_score")},
                gauge={
                    "axis": {"range": [None, 100]},
                    "bar": {"color": "darkblue"},
                    "steps": [
                        {"range": [0, 40], "color": "lightgray"},
                        {"range": [40, 60], "color": "yellow"},
                        {"range": [60, 80], "color": "lightgreen"},
                        {"range": [80, 100], "color": "green"},
                    ],
                },
            )
        )
        fig_gauge.update_layout(height=280)
        st.plotly_chart(fig_gauge, use_container_width=True)

        m1, m2 = st.columns(2)
        with m1:
            st.metric(t("priority"), str(project_to_show.get("priority", "N/D")))
            st.metric(t("viability_score"), f"{int(viability_score)}/100")
            st.metric(
                t("time_reduction_achieved"), f"{_safe_float(project_to_show.get('time_reduction_percent')):.0f}%"
            )
        with m2:
            st.metric(t("monthly_savings"), f"${_safe_float(project_to_show.get('monthly_savings')):,.0f}")
            st.metric(t("annual_savings"), f"${_safe_float(project_to_show.get('annual_savings')):,.0f}")
            st.metric(t("first_year_roi"), f"{_safe_float(project_to_show.get('roi_first_year')):.1f}%")

        st.info(f"ðŸ“ {project_to_show.get('recommendation', '')}")
