from unittest.mock import MagicMock, patch


def _make_mock_state(initial: dict | None = None) -> MagicMock:
    state = MagicMock()
    data = dict(initial or {})
    state.__contains__ = lambda s, k: k in data
    state.__getitem__ = lambda s, k: data[k]
    state.__setitem__ = lambda s, k, v: data.__setitem__(k, v)
    state.get = lambda k, default=None: data.get(k, default)
    state._data = data
    return state


def test_init_state_sets_all_required_keys():
    mock_state = _make_mock_state()
    with patch("streamlit.session_state", mock_state):
        import importlib

        import ui.state as state_mod

        importlib.reload(state_mod)
        state_mod.init_state()

    required_keys = ["language", "edit_mode", "selected_project_id", "temp_calculation", "latest_results", "active_tab"]
    for key in required_keys:
        assert key in mock_state._data, f"Missing key: {key}"


def test_init_state_is_idempotent():
    mock_state = _make_mock_state({"language": "pt"})
    with patch("streamlit.session_state", mock_state):
        import importlib

        import ui.state as state_mod

        importlib.reload(state_mod)
        state_mod.init_state()
        state_mod.init_state()

    assert mock_state._data["language"] == "pt"
