# Safety Alerts – Auto Image Filing (MVP)

This project is an MVP for bulk image/document filing from scanned records (bulletins, attendance sheets, records, minutes, notes, etc.).

## What it does

- Scans a folder of image files.
- Runs OCR to read visible text.
- Infers a **document type** from keyword rules.
- Extracts a date when possible.
- Generates a clean, consistent filename.
- Moves each file into the folder it belongs in.

Example output path:

`church_bulletin/1965/church_bulletin_1965-01-03_voice_of_the_cross_1.jpg`

## Current routing logic

The script currently routes files to:

`<doc_type>/<year|undated>/filename.ext`

Examples:

- Attendance sheet scans -> `attendance_sheet/1965/...`
- Church bulletin scans (“VOICE OF THE CROSS”) -> `church_bulletin/1965/...`
- Low OCR confidence -> `unknown/undated/...`

## Quick start

### 1) Install system OCR

This project uses Tesseract OCR.

- Ubuntu/Debian:

```bash
sudo apt-get update && sudo apt-get install -y tesseract-ocr
```

- macOS:

```bash
brew install tesseract
```

### 2) Install Python dependencies

```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

### 3) Run in dry-run mode first

```bash
python src/auto_filer.py --input ./scans --output ./organized --dry-run
```

### 4) Apply filing (rename + move)

```bash
python src/auto_filer.py --input ./scans --output ./organized
```

## Command options

```bash
python src/auto_filer.py --help
```

Key options:

- `--input`: folder with images.
- `--output`: root folder where organized files will be written (default: input folder).
- `--recursive`: include nested folders.
- `--dry-run`: print proposed changes only.
- `--min-text-chars`: minimum OCR text before using fallback naming.
- `--conf-threshold`: minimum OCR confidence to keep a text token.

## Naming format

`<doc_type>_<yyyy-mm-dd|undated>_<title_slug>_<counter>.<ext>`

## Next upgrades (recommended)

1. Add layout analysis for multi-column scans.
2. Add handwriting OCR model for notes.
3. Add human-review queue for low-confidence files.
4. Store extracted metadata in SQLite/PostgreSQL.
5. Add web UI for drag-drop batch jobs.
