from asr_omni.app import build_parser


def test_default_hotkey_is_alt_h():
    args = build_parser().parse_args([])

    assert args.hotkey == "alt+h"
