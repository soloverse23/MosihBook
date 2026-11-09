"""The prompt -> image -> review loop, without any network calls."""
import json
import shutil
from pathlib import Path

import pytest

from bookforge import spec
from bookforge.art import generate, prompting, review
from bookforge.art.lint import lint
from bookforge.providers.openai_images import ModerationBlocked, flex_size
from bookforge.project import Project

EXAMPLES = Path(__file__).resolve().parent.parent / "examples"


@pytest.fixture
def project(tmp_path):
    shutil.copy(EXAMPLES / "picture-book" / "book.yaml", tmp_path / "book.yaml")
    return Project(tmp_path / "book.yaml", mock=True)


def test_reference_legend_numbers_each_image():
    refs = [prompting.Ref(Path("a.png"), "character reference for Pip."), prompting.Ref(Path("b.png"), prompting.STYLE_ROLE)]
    p = prompting.with_refs("SCENE: x", refs, note="Pip smaller", fix="remove the sign")
    assert "Image 1: character reference for Pip" in p and "Image 2: style reference" in p
    assert p.index("ATTACHED IMAGES") < p.index("SCENE") < p.index("ART DIRECTOR NOTE") < p.index("CORRECTION")


def test_pages_get_character_and_style_refs(project, monkeypatch):
    seen = {}
    real = project.book.images
    from bookforge.providers import mock

    def spy(self, prompt, size, refs, quality=None):
        seen[prompt.split("SCENE: ")[1][:30]] = [f"{r.parent.name}/{r.name}" for r in refs]
        return orig(self, prompt, size, refs, quality)
    orig = mock.MockProvider.generate
    monkeypatch.setattr(mock.MockProvider, "generate", spy)
    generate.run(project)
    page7 = next(v for k, v in seen.items() if k.startswith("Grandma Owl handing"))
    # character sheets come from the character directory, the style anchor from the art folder
    assert page7 == ["pip/sheet.png", "grandma-owl/sheet.png", "art-mock/cover-front.png"]
    assert real.style_anchor


def test_failed_review_is_flagged_never_redrawn(project, monkeypatch):
    bad = {"score": 4, "has_text": True, "character_issues": [], "anatomy_issues": [], "composition_issues": [],
           "style_issues": [], "fix": "Remove the writing on the signpost."}
    calls = []
    monkeypatch.setattr(generate, "get_reviewer", lambda s: type("R", (), {"review": lambda *a: calls.append(1) or bad})())
    failures = generate.run(project, only={"p002"})
    assert len(calls) == 1 and "p002" in failures  # one image, one review, no automatic second attempt
    generate.run(project, only={"p002"})
    assert len(calls) == 1  # a second run reuses the cached image and verdict: nothing is paid twice


def test_redo_draws_a_fresh_image_with_the_note(project):
    generate.run(project, only={"p002"})
    first = json.loads((project.build / "review-mock.json").read_text())["_chosen"]["p002"]["key"]
    generate.run(project, only={"p002"}, bump={"p002"}, notes={"p002": "Pip smaller"})
    second = json.loads((project.build / "review-mock.json").read_text())["_chosen"]["p002"]["key"]
    assert first != second


def test_review_failure_is_reported_not_fatal(project, monkeypatch):
    bad = {"score": 3, "has_text": False, "character_issues": ["Pip has no scarf"], "anatomy_issues": [],
           "composition_issues": [], "style_issues": [], "fix": "Give Pip his mustard scarf."}
    monkeypatch.setattr(generate, "get_reviewer", lambda s: type("R", (), {"review": lambda *a: bad})())
    failures = generate.run(project, only={"p002"})
    assert "Pip has no scarf" in failures["p002"]
    assert project.art_path("p002").exists()  # best attempt still placed so the book can build
    assert "p002" in (project.build / "review.html").read_text()


def test_moderation_block_skips_one_image(project, monkeypatch):
    from bookforge.providers import mock

    def blocked(self, prompt, size, refs, quality=None):
        raise ModerationBlocked("moderation_blocked")
    monkeypatch.setattr(mock.MockProvider, "generate", blocked)
    failures = generate.run(project, only={"p003"})
    assert "moderation" in failures["p003"]


def test_pilot_limits_scope(project):
    generate.run(project, pilot=2)
    made = sorted(f.stem for f in project.art.glob("*.png"))
    assert made == ["char-grandma-owl", "char-pip", "cover-front", "p001", "p002"]


def test_size_stays_in_non_experimental_range():
    for aspect in (1, 0.66, 1.98, 3):
        w, h = flex_size(aspect, 2560 * 1440)
        assert w % 16 == h % 16 == 0 and 655_360 <= w * h <= 2560 * 1440 + 16 * (w + h)


def test_lint_reports_only_serious_problems():
    data = spec.load(EXAMPLES / "picture-book" / "book.yaml").model_dump()
    data["pages"][1]["prompt"] = 'a shop sign that says "Open" above Pip in a Pixar style street'
    issues = lint(spec.Book.model_validate(data))
    page2 = [i for i in issues if i.where == "page 2"]
    assert len(page2) == 1 and "studio/franchise" in page2[0].message  # words in the prompt are no longer flagged
    assert all(i.level == "error" for i in issues)


def test_passed_rule():
    ok = {"score": 8, "has_text": False, "character_issues": [], "anatomy_issues": []}
    assert review.passed(ok, 7)
    assert not review.passed({**ok, "has_text": True}, 7)
    assert not review.passed({**ok, "score": 6}, 7)


def test_lettered_pass_rule_checks_spelling_not_presence_of_text():
    ok = {"score": 9, "has_text": True, "text_errors": [], "text_legible": True, "text_in_safe_area": True,
          "character_issues": [], "anatomy_issues": []}
    assert review.passed(ok, 7, lettered=True) and not review.passed(ok, 7)
    assert not review.passed({**ok, "text_errors": ["'wigles' should be 'wiggles'"]}, 7, lettered=True)
    assert not review.passed({**ok, "text_in_safe_area": False}, 7, lettered=True)


def test_misspelled_lettering_is_flagged_once(project, monkeypatch):
    bad = {"score": 8, "has_text": True, "text_errors": ["'Willomere' should be 'Willowmere'"], "text_legible": True,
           "text_in_safe_area": True, "character_issues": [], "anatomy_issues": [], "composition_issues": [],
           "style_issues": [], "fix": "Spell 'Willowmere' with a w after the double l."}
    seen = []

    class AlwaysMisspelled:
        def review(self, image, prompt, refs, expected_text=""):
            seen.append(expected_text)
            return bad if expected_text.startswith("In the woods") else {**bad, "text_errors": [], "fix": ""}
    monkeypatch.setattr(generate, "get_reviewer", lambda s: AlwaysMisspelled())
    failures = generate.run(project, only={"p001"})
    assert [e for e in seen if e.startswith("In the woods")] and len(seen) == 1
    assert "Willomere" in failures["p001"]


def test_paid_art_is_never_redrawn_without_redo(tmp_path, monkeypatch):
    """A changed cover or page prompt must not silently re-buy pages: only Redo redraws, and the change is flagged."""
    from bookforge import settings as app_settings
    from bookforge.providers.mock import MockProvider
    shutil.copy(EXAMPLES / "picture-book" / "book.yaml", tmp_path / "book.yaml")
    p = Project(tmp_path / "book.yaml")  # real (non-mock) project, fake provider
    p.book.images.review = False
    calls, spent = [], []

    class Counting(MockProvider):
        model = "fake"

        def generate(self, prompt, size, refs, quality=None):
            calls.append(prompt)
            return super().generate(prompt, size, refs, quality)
    monkeypatch.setattr(generate, "get_provider", lambda s: Counting(s.max_pixels))
    monkeypatch.setattr(generate.characters, "lock", lambda *a: None)
    monkeypatch.setattr(generate.characters, "adopt", lambda *a: None)
    monkeypatch.setattr(app_settings, "record_spend", lambda usd, book, slot: spent.append(slot))
    generate.run(p)
    first = len(calls)
    assert first and len(spent) == first
    p.book.cover_prompt += ", at sunset"
    p.book.pages[1].prompt += ", in the rain"
    failures = generate.run(p)
    assert len(calls) == first  # nothing redrawn
    assert "Redo" in failures["p002"]
    generate.run(p, only={"p002"}, bump={"p002"})
    assert len(calls) == first + 1
