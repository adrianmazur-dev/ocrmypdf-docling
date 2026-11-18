# Repository Guidelines

## Project Structure

The Python package lives in `src/ocrmypdf_docling/`. `plugin.py` registers OCRmyPDF hooks and CLI options. `engine.py` calls Docling Serve and maps DCC word boxes, reading order, and table cells into OCRmyPDF's text layer. `options.py` defines connection settings, `languages.py` maps language codes, and `hocr.py` serializes OCR results for hOCR callers. Packaging and dependencies live in `pyproject.toml` and `uv.lock`. Keep local PDFs and generated comparison files in `.temp/` and out of commits.

## Build and Development

- `uv sync --locked` installs the project and development tools using the lockfile. The repository defaults to Python 3.14.
- `uv run ocrmypdf --docling -l pol --sidecar output.txt input.pdf output.pdf` runs the installed plugin. Start the DCC-enabled Docling Serve image using the instructions in `README.md`.
- `uv run ruff format --check src` checks formatting. Run `uv run ruff check src` for linting and `uv run ty check` for type checking.
- `uv build` builds the source distribution and wheel in `dist/`.

## Coding Style

Use four-space indentation, double quotes, and Ruff formatting. Use `snake_case` for functions and modules, `PascalCase` for classes, and type hints on public functions. Keep OCRmyPDF registration in `plugin.py` and OCR response handling in `engine.py`.

## Git

Prefer short conventional commits such as `feat: preserve table reading order`.
