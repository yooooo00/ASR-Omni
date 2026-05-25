from asr_omni.glossary import Glossary, GlossaryEntry


def test_glossary_replaces_cloud_code_case_insensitively():
    glossary = Glossary([GlossaryEntry("cloud code", "claude code")])

    assert glossary.apply("open Cloud Code now") == "open claude code now"


def test_default_glossary_contains_claude_code_replacement():
    glossary = Glossary.default()

    assert glossary.apply("use cloud code") == "use claude code"
