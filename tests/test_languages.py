"""A book in any of the supported languages: its own words, its typography, fonts that have every letter."""
from pathlib import Path

import pytest
import yaml
from pypdf import PdfReader

from bookforge import spec, translate, words
from bookforge.art import generate
from bookforge.layout.base import _LANGUAGE, missing_glyphs, para_html, theme_for
from bookforge.layout.cover import build_cover
from bookforge.layout.render import build_interior
from bookforge.plan import plan
from bookforge.preflight import check
from bookforge.project import Project

EXAMPLES = Path(__file__).resolve().parent.parent / "examples"
LETTERS = {"English": "", "French": "àâçéèêëîïôœùûüÿ«»", "German": "äöüßÄÖÜ„“",
           "Romanian": "ăâîșțĂÂÎȘȚ", "Spanish": "áéíñóúü¡¿"}


def example(name: str, **over) -> dict:
    data = yaml.safe_load((EXAMPLES / name / "book.yaml").read_text())
    data.update(over)
    return data


@pytest.mark.parametrize("given,expected", [
    ("French", "French"), ("fr", "French"), ("Français", "French"), ("germany", "German"), ("Deutsch", "German"),
    ("română", "Romanian"), ("ro", "Romanian"), ("Español", "Spanish"), ("es", "Spanish"), ("", "English"),
    (None, "English")])
def test_language_names_and_codes(given, expected):
    assert words.canonical(given) == expected


def test_only_supported_languages():
    assert spec.Book.model_validate(example("picture-book", language="fr")).language == "French"
    with pytest.raises(ValueError, match="not supported"):
        spec.Book.model_validate(example("picture-book", language="Persian"))


@pytest.mark.parametrize("language", words.LANGUAGES)
def test_every_font_has_every_letter(language):
    for kind in ("picture-book", "storybook", "comic"):
        book = spec.Book.model_validate(example(kind, language=language, about_author=LETTERS[language]))
        t = theme_for(book)
        for font in (t.body, t.body_bold, t.heading):
            text = LETTERS[language] + "".join(words.TABLE[language].values())
            assert not missing_glyphs(font, text), (kind, font)


@pytest.mark.parametrize("language", words.LANGUAGES)
def test_the_end_is_lettered_in_the_book_language(language):
    data = example("picture-book", language=language)
    data["images"]["text_in_art"] = True
    end = next(s for s in plan(spec.Book.model_validate(data)) if s.id == "the-end")
    assert end.lettering.text == words.TABLE[language]["the_end"]


def test_own_words_win():
    data = example("picture-book", language="French", words={"the_end": "Fin de l'histoire"})
    assert words.word(spec.Book.model_validate(data), "the_end") == "Fin de l'histoire"
    assert words.word(spec.Book.model_validate(data), "name") == "Prénom"


def test_french_punctuation_never_starts_a_line():
    _LANGUAGE.set("French")
    assert para_html("« Oui ! » dit-il : bien ; non ?") == "« Oui ! » dit-il : bien ; non ?"
    _LANGUAGE.set("English")
    assert para_html("Oui ! ok") == "Oui ! ok"


@pytest.mark.parametrize("language", ["French", "Romanian"])
def test_closing_pages_print_in_the_book_language(tmp_path, language):
    data = example("picture-book", language=language, about_author="x")
    data["images"]["text_in_art"] = False
    (tmp_path / "book.yaml").write_text(yaml.safe_dump(data, allow_unicode=True))
    p = Project(tmp_path / "book.yaml", mock=True)
    generate.run(p, log=lambda m: None)
    build_interior(p)
    build_cover(p)
    assert check(p)["ok"]
    text = " ".join(pg.extract_text() for pg in PdfReader(p.interior_pdf).pages).replace(" ", " ")
    for key in ("the_end", "about_author"):
        assert words.TABLE[language][key].replace(" ", " ") in text
    assert "The End" not in text and "All rights reserved" not in text


def test_translation_keeps_placeholders_and_own_words():
    data = example("picture-book", words={"the_end": "The very end", "copyright": "© {year} {author}"})
    texts = translate.texts(data)
    assert texts["words.the_end"] == "The very end"
    assert translate.check(texts, {**texts, "words.copyright": "© {author}"}) == ["words.copyright: keep {year} exactly as it is"]
    assert translate.apply(data, {"words.the_end": "La toute fin"})["words"]["the_end"] == "La toute fin"
