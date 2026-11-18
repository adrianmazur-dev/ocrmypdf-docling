from os import environ
from pathlib import Path
from typing import Literal, cast

import httpx
from ocrmypdf import BoundingBox, OcrClass, OcrElement, OcrOptions
from ocrmypdf.exceptions import BadArgsError, SubprocessOutputError
from ocrmypdf.pluginspec import OcrEngine, OrientationConfidence
from PIL import Image
from pydantic import BaseModel, FiniteFloat, ValidationError

from .hocr import to_hocr
from .languages import docling_language
from .options import DoclingOptions
from .version import plugin_version

type _Origin = Literal["TOPLEFT", "BOTTOMLEFT"]


class _Rectangle(BaseModel):
    r_x0: FiniteFloat
    r_y0: FiniteFloat
    r_x1: FiniteFloat
    r_y1: FiniteFloat
    r_x2: FiniteFloat
    r_y2: FiniteFloat
    r_x3: FiniteFloat
    r_y3: FiniteFloat
    coord_origin: _Origin

    def bounds(self) -> BoundingBox:
        xs = (self.r_x0, self.r_x1, self.r_x2, self.r_x3)
        ys = (self.r_y0, self.r_y1, self.r_y2, self.r_y3)
        return BoundingBox(min(xs), min(ys), max(xs), max(ys))


class _Cell(BaseModel):
    text: str
    rect: _Rectangle
    confidence: FiniteFloat | None = None
    from_ocr: bool


class _PageGeometry(BaseModel):
    rect: _Rectangle


class _SegmentedPage(BaseModel):
    dimension: _PageGeometry
    textline_cells: list[_Cell]
    word_cells: list[_Cell]


def _pixel_box(rect: _Rectangle, frame: BoundingBox, page: BoundingBox) -> BoundingBox:
    box = rect.bounds()
    if rect.coord_origin == "BOTTOMLEFT":
        top, bottom = frame.bottom - box.bottom, frame.bottom - box.top
    else:
        top, bottom = box.top - frame.top, box.bottom - frame.top
    sx, sy = page.width / frame.width, page.height / frame.height
    result = BoundingBox(
        max(0.0, min(page.width, (box.left - frame.left) * sx)),
        max(0.0, min(page.height, top * sy)),
        max(0.0, min(page.width, (box.right - frame.left) * sx)),
        max(0.0, min(page.height, bottom * sy)),
    )
    if result.width == 0 or result.height == 0:
        raise ValueError("an OCR cell has an empty bounding box in the page image")
    return result


def _overlap(first: BoundingBox, second: BoundingBox) -> float:
    width = min(first.right, second.right) - max(first.left, second.left)
    height = min(first.bottom, second.bottom) - max(first.top, second.top)
    return max(0.0, width) * max(0.0, height)


def _map_page(segmented: _SegmentedPage, page: OcrElement) -> str:
    assert page.bbox is not None
    frame = segmented.dimension.rect.bounds()
    if frame.width <= 0 or frame.height <= 0:
        raise ValueError("the response has invalid page dimensions")

    lines = [
        cell for cell in segmented.textline_cells if cell.from_ocr and cell.text.strip()
    ]
    words = [
        cell for cell in segmented.word_cells if cell.from_ocr and cell.text.strip()
    ]
    if lines and not words:
        raise ValueError(
            "the server returned text without word boxes; use the pp-ocrv6 preset"
        )
    if words and not lines:
        raise ValueError("the server returned words without line boxes")

    line_boxes = [_pixel_box(line.rect, frame, page.bbox) for line in lines]
    page.children = [OcrElement(OcrClass.LINE, bbox) for bbox in line_boxes]
    for word in words:
        box = _pixel_box(word.rect, frame, page.bbox)
        best_line = max(
            range(len(line_boxes)), key=lambda index: _overlap(line_boxes[index], box)
        )
        if _overlap(line_boxes[best_line], box) == 0:
            raise ValueError("a word box does not overlap any text line")
        page.children[best_line].children.append(
            OcrElement(OcrClass.WORD, box, text=word.text, confidence=word.confidence)
        )

    if any(not line.children for line in page.children):
        raise ValueError("the server returned a text line without word boxes")
    return "".join(f"{line.get_text_recursive()}\n" for line in page.children)


def _fetch_page(
    input_file: Path, settings: DoclingOptions, languages: list[str]
) -> _SegmentedPage:
    data = {
        "from_formats": "image",
        "to_formats": "json",
        "include_word_boxes": "true",
        "do_ocr": "true",
        "force_ocr": "true",
        "do_table_structure": "false",
        "ocr_preset": settings.preset,
        "ocr_lang": languages,
    }
    headers = {"Accept": "application/json"}
    if api_key := environ.get("DOCLING_SERVE_API_KEY"):
        headers["X-Api-Key"] = api_key
    endpoint = f"{str(settings.url).rstrip('/')}/v1/convert/file"
    with input_file.open("rb") as image:
        response = httpx.post(
            endpoint,
            files={"files": (input_file.name, image)},
            data=data,
            headers=headers,
            timeout=settings.timeout,
        )
    response.raise_for_status()
    result = response.json()
    if not isinstance(result, dict) or result.get("status") != "success":
        raise ValueError("Docling Serve did not complete the conversion successfully")
    document = result.get("document")
    pages = document.get("word_boxes") if isinstance(document, dict) else None
    if not isinstance(pages, dict) or "1" not in pages:
        raise ValueError(
            "response lacks word_boxes for the uploaded image; enable the DCC extension"
        )
    return _SegmentedPage.model_validate(pages["1"])


class DoclingEngine(OcrEngine):
    """OCR using Docling Serve with the DCC word-box extension."""

    version = staticmethod(plugin_version)

    def __str__(self) -> str:
        return f"ocrmypdf-docling {self.version()}"

    @staticmethod
    def creator_tag(options: OcrOptions) -> str:
        settings = cast(DoclingOptions, options.docling)
        return f"ocrmypdf-docling {plugin_version()} ({settings.preset})"

    @staticmethod
    def languages(options: OcrOptions) -> set[str]:
        return set()  # The server validates the languages for the selected preset.

    @staticmethod
    def get_orientation(input_file: Path, options: OcrOptions) -> OrientationConfidence:
        return OrientationConfidence(0, 0.0)

    @staticmethod
    def supports_generate_ocr() -> bool:
        return True

    @staticmethod
    def generate_ocr(
        input_file: Path,
        options: OcrOptions,
        page_number: int = 0,
    ) -> tuple[OcrElement, str]:
        settings = cast(DoclingOptions, options.docling)
        try:
            languages = [docling_language(code) for code in options.languages]
        except ValueError as error:
            raise BadArgsError(f"Invalid OCR language: {error}") from error

        prefix = f"Docling Serve OCR failed on page {page_number + 1}"
        try:
            segmented = _fetch_page(input_file, settings, languages)
            with Image.open(input_file) as image:
                dpi = image.info.get("dpi", (300, 300))
                page = OcrElement(
                    OcrClass.PAGE,
                    BoundingBox(0, 0, image.width, image.height),
                    dpi=float(dpi[0] if isinstance(dpi, tuple) else dpi),
                    page_number=page_number,
                    language=options.languages[0] if options.languages else None,
                )
                text = _map_page(segmented, page)
            return page, text
        except httpx.TimeoutException as error:
            raise SubprocessOutputError(
                f"{prefix}: request timed out after {settings.timeout:g} s"
            ) from error
        except httpx.HTTPStatusError as error:
            raise SubprocessOutputError(
                f"{prefix}: HTTP {error.response.status_code}"
            ) from error
        except httpx.RequestError as error:
            raise SubprocessOutputError(
                f"{prefix}: {type(error).__name__} contacting the server"
            ) from error
        except ValidationError as error:
            raise SubprocessOutputError(
                f"{prefix}: invalid DCC word-box data"
            ) from error
        except ValueError as error:
            raise SubprocessOutputError(f"{prefix}: {error}") from error

    @staticmethod
    def generate_hocr(
        input_file: Path,
        output_hocr: Path,
        output_text: Path,
        options: OcrOptions,
    ) -> None:
        page, text = DoclingEngine.generate_ocr(input_file, options)
        output_hocr.write_text(to_hocr(page), encoding="utf-8")
        output_text.write_text(text, encoding="utf-8")

    @staticmethod
    def generate_pdf(
        input_file: Path,
        output_pdf: Path,
        output_text: Path,
        options: OcrOptions,
    ) -> None:
        raise NotImplementedError("Docling requires --pdf-renderer auto or fpdf2")
