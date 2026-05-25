from asr_omni.app import build_glossary, build_preview_queue, parse_args, register_hotkeys


def test_default_hotkeys_include_ctrl_h_and_alt_h():
    args = parse_args([])

    assert args.hotkeys == ["ctrl+h", "alt+h"]
    assert args.language == "auto"


def test_default_segmentation_prefers_continuous_dictation():
    args = parse_args([])

    assert args.silence_seconds == 2.0
    assert args.max_segment_seconds == 30.0
    assert args.preview_interval_seconds == 1.0
    assert args.min_preview_seconds == 1.0


def test_preview_is_disabled_by_default():
    args = parse_args([])

    assert args.preview is False
    assert build_preview_queue(args) is None


def test_preview_can_be_enabled_with_cli():
    args = parse_args(["--preview"])

    assert args.preview is True
    assert build_preview_queue(args) is not None


def test_no_preview_cli_overrides_settings_file(tmp_path):
    settings_file = tmp_path / "settings.json"
    settings_file.write_text('{"preview": true}', encoding="utf-8")

    args = parse_args(["--config-file", str(settings_file), "--no-preview"])

    assert args.preview is False


def test_default_glossary_is_enabled():
    args = parse_args([])

    assert args.glossary_file is None
    assert args.no_default_glossary is False


def test_build_glossary_merges_default_and_file(tmp_path):
    glossary_file = tmp_path / "glossary.tsv"
    glossary_file.write_text("foo\tbar\n", encoding="utf-8")
    args = parse_args(["--glossary-file", str(glossary_file)])

    glossary = build_glossary(args)

    assert glossary.apply("cloud code and foo") == "claude code and bar"


def test_parse_args_loads_hotkeys_from_settings_file(tmp_path):
    settings_file = tmp_path / "settings.json"
    settings_file.write_text('{"hotkeys": ["ctrl+alt+h", "alt+h"]}', encoding="utf-8")

    args = parse_args(["--config-file", str(settings_file)])

    assert args.hotkeys == ["ctrl+alt+h", "alt+h"]


def test_parse_args_supports_legacy_hotkey_from_settings_file(tmp_path):
    settings_file = tmp_path / "settings.json"
    settings_file.write_text('{"hotkey": "ctrl+alt+h"}', encoding="utf-8")

    args = parse_args(["--config-file", str(settings_file)])

    assert args.hotkeys == ["ctrl+alt+h"]


def test_cli_hotkey_overrides_settings_file(tmp_path):
    settings_file = tmp_path / "settings.json"
    settings_file.write_text('{"hotkeys": ["ctrl+alt+h", "alt+h"]}', encoding="utf-8")

    args = parse_args([
        "--config-file",
        str(settings_file),
        "--hotkey",
        "shift+h",
        "--hotkey",
        "ctrl+h",
    ])

    assert args.hotkeys == ["shift+h", "ctrl+h"]


def test_parse_args_none_uses_sys_argv(monkeypatch):
    monkeypatch.setattr("sys.argv", ["app.py", "--hotkey", "alt+h"])

    args = parse_args(None)

    assert args.hotkeys == ["alt+h"]


def test_register_hotkeys_registers_every_hotkey():
    calls = []

    class FakeKeyboard:
        @staticmethod
        def add_hotkey(hotkey, callback):
            calls.append((hotkey, callback))

    def callback():
        return None

    register_hotkeys(FakeKeyboard, ["ctrl+h", "alt+h"], callback)

    assert calls == [("ctrl+h", callback), ("alt+h", callback)]
