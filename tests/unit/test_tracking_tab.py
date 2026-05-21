import inspect
from ui.tabs import tracking


def test_render_tracking_tab_is_defined_once():
    source = inspect.getsource(tracking)
    count = source.count("def render_tracking_tab(")
    assert count == 1, f"render_tracking_tab definida {count} veces, esperado 1"


def test_render_tracking_tab_includes_feedback_logic():
    source = inspect.getsource(tracking.render_tracking_tab)
    assert (
        "auto_process_feedback" in source or "get_tracking_source" in source
    ), "La función activa no tiene la lógica de feedback/source — se está usando la versión simplificada"
