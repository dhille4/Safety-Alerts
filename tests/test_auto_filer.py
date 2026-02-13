from pathlib import Path
import sys

sys.path.append(str(Path(__file__).resolve().parents[1] / "src"))

from auto_filer import (
    create_filename,
    detect_doc_type,
    extract_date,
    infer_title,
    make_relative_folder,
    slugify_title,
)


def test_detect_doc_type_minutes():
    text = "Board meeting minutes and agenda approved with quorum present"
    assert detect_doc_type(text) == "minutes"


def test_detect_doc_type_bulletin():
    text = "VOICE OF THE CROSS LUTHERAN CHURCH OF THE CROSS THE SERVICE"
    assert detect_doc_type(text) == "church_bulletin"


def test_extract_date_iso():
    text = "Meeting held on 2024-10-03 in the main office"
    assert extract_date(text) == "2024-10-03"


def test_extract_date_month_name():
    text = "SECOND SUNDAY AFTER CHRISTMAS January 3, 1965"
    assert extract_date(text) == "1965-01-03"


def test_slugify_title_filters_stopwords():
    text = "The meeting notes for the annual heritage committee review"
    slug = slugify_title(text)
    assert "the" not in slug
    assert "notes" in slug


def test_infer_title_attendance_sheet():
    text = "ATTENDANCE SHEET FOR WORSHIP SERVICE"
    assert infer_title(text, "attendance_sheet") == "attendance_sheet"


def test_make_relative_folder():
    assert make_relative_folder("church_bulletin", "1965-01-10") == Path("church_bulletin/1965")


def test_create_filename_format():
    name = create_filename("minutes", "2024-03-11", "board_meeting", ".jpg", 2)
    assert name == "minutes_2024-03-11_board_meeting_2.jpg"
