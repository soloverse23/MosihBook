import pytest

from bookforge import kdp


def test_interior_page_size_has_outside_bleed_only():
    i = kdp.Interior(8.5, 8.5, 32)
    assert (i.page_w, i.page_h) == (8.625, 8.75)


def test_recto_verso_trim_offset():
    i = kdp.Interior(6, 9, 100)
    assert i.trim_x(1) == 0 and i.trim_x(2) == kdp.BLEED


def test_safe_box_mirrors_gutter():
    i = kdp.Interior(6, 9, 200)  # 151-300 pages -> 0.5" gutter
    rx, _, rw, _ = i.safe_box(1)
    vx, _, vw, _ = i.safe_box(2)
    assert rx == 0.5 and rw == 6 - 0.5 - 0.375
    assert vx == kdp.BLEED + 0.375 and vw == rw


@pytest.mark.parametrize("pages,g", [(24, 0.375), (150, 0.375), (151, 0.5), (301, 0.625), (828, 0.875)])
def test_gutter_steps(pages, g):
    assert kdp.gutter(pages) == g


def test_page_count_padding():
    assert kdp.pad_page_count(7) == 24
    assert kdp.pad_page_count(31) == 32


def test_cover_dimensions_match_kdp_formula():
    c = kdp.Cover(8.5, 8.5, 28, "premium_color")
    assert c.spine == pytest.approx(28 * 0.002347)
    assert c.width == pytest.approx(0.125 + 8.5 + 0.065716 + 8.5 + 0.125)
    assert c.height == 8.75
    assert not c.spine_text_allowed
    assert kdp.Cover(6, 9, 80, "cream_bw").spine_text_allowed


def test_barcode_box_on_back_cover():
    c = kdp.Cover(6, 9, 120, "white_bw")
    x, y, w, h = c.barcode_box()
    assert x + w <= c.spine_x and y >= kdp.BLEED
