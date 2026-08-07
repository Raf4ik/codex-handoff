from codex_handoff.gui.i18n import EN, RU, normalize_language, text


def test_english_is_default_and_unknown_languages_fall_back() -> None:
    assert normalize_language(None) == "en"
    assert normalize_language("de") == "en"
    assert text("de", "settings") == "Settings"


def test_russian_catalog_covers_every_interface_key() -> None:
    assert RU.keys() == EN.keys()
    assert text("ru", "settings") == "Настройки"
