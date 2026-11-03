"""Book structure templates and code-drawn mazes."""
import pytest
from pydantic import ValidationError

from bookforge import maze, settings, templates


@pytest.fixture(autouse=True)
def home(tmp_path, monkeypatch):
    monkeypatch.setattr(settings, "PATH", tmp_path / "settings.json")


def test_builtin_anahita_has_40_pages():
    t = templates.get("anahita-40")
    assert t and t.page_count() == 40
    assert [s.kind for s in t.active()][:3] == ["parents_note", "story", "comprehension"]


def test_save_overrides_builtin_and_delete_restores():
    t = templates.get("anahita-40").model_dump()
    t["sections"][1]["pages"] = 16
    templates.save(t)
    assert templates.get("anahita-40").page_count() == 38
    assert templates.delete("anahita-40")
    assert templates.get("anahita-40").page_count() == 40


def test_disabled_sections_drop_out_of_structure():
    secs = [{"kind": "story", "pages": 10}, {"kind": "maze", "pages": 1, "enabled": False}]
    text = templates.structure_text(secs)
    assert "Interior pages: 10." in text and "maze" not in text


def test_unknown_kind_rejected():
    with pytest.raises(ValidationError):
        templates.Template(id="x", name="x", sections=[{"kind": "karaoke"}])


@pytest.mark.parametrize("seed", range(40))
def test_maze_always_solvable_and_perfect(seed):
    m = maze.generate(cols=3 + seed % 9, rows=4 + seed % 7, seed=seed)
    path = m.solve()
    assert path[0] == m.start and path[-1] == m.goal
    openings = sum(bin(v).count("1") for row in m.open for v in row) // 2
    assert openings == m.cols * m.rows - 1  # a spanning tree: every cell reachable, no loops


def test_maze_draws(tmp_path):
    from reportlab.pdfgen import canvas
    c = canvas.Canvas(str(tmp_path / "m.pdf"))
    maze.draw(c, maze.generate(8, 10, 3), 50, 50, 400, 500, solution=True)
    c.save()
    assert (tmp_path / "m.pdf").stat().st_size > 1000
