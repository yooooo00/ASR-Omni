from asr_omni.control_window import ControlWindowState, get_control_window_style


class FakeApp:
    def __init__(self):
        self.recording = False
        self.toggle_calls = 0

    def toggle_recording(self):
        self.toggle_calls += 1
        self.recording = not self.recording


def test_control_window_button_toggles_recording_state():
    app = FakeApp()
    state = ControlWindowState(app)

    assert state.snapshot()["label"] == "Start"

    state.toggle()

    assert app.toggle_calls == 1
    assert state.snapshot()["label"] == "Recording"


def test_control_window_style_is_topmost_and_compact():
    style = get_control_window_style()

    assert style["topmost"] is True
    assert style["geometry"] == "144x54+40+160"
