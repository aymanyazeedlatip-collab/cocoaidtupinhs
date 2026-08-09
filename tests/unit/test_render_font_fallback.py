from pathlib import Path


def _directory_candidates(directory: Path) -> dict[str, list[Path]]:
    return {
        "regular": [directory],
        "bold": [directory],
        "italic": [directory],
        "bold_italic": [directory],
    }


def test_legacy_pdf_font_loader_does_not_treat_directory_as_font(tmp_path, monkeypatch):
    from app.reports import pdf

    monkeypatch.setattr(pdf, "_font_candidates", lambda: _directory_candidates(tmp_path))
    assert pdf._register_fonts() == (
        "Times-Roman",
        "Times-Bold",
        "Times-Italic",
        "Times-BoldItalic",
    )


def test_phase10_pdf_font_loader_does_not_treat_directory_as_font(tmp_path, monkeypatch):
    from app.coco_pilot import reports

    monkeypatch.setattr(reports, "_font_candidates", lambda: _directory_candidates(tmp_path))
    assert reports._register_report_fonts() == (
        "Times-Roman",
        "Times-Bold",
        "Times-Italic",
        "Times-BoldItalic",
    )


def test_first_font_file_requires_real_file(tmp_path):
    from app.reports import pdf
    from app.coco_pilot import reports

    missing = tmp_path / "missing.ttf"
    directory = tmp_path / "font-dir"
    directory.mkdir()
    fake_font = tmp_path / "font.ttf"
    fake_font.write_bytes(b"not-a-real-font")

    assert pdf._first_font_file([missing, directory]) is None
    assert reports._first_report_font_file([missing, directory]) is None
    assert pdf._first_font_file([directory, fake_font]) == fake_font
    assert reports._first_report_font_file([directory, fake_font]) == fake_font
