from argparse import ArgumentParser

from ocrmypdf import OcrOptions, hookimpl
from ocrmypdf.exceptions import BadArgsError
from pydantic import ValidationError

from .engine import DoclingEngine
from .options import DoclingOptions


@hookimpl
def register_options() -> dict[str, type[DoclingOptions]]:
    return {"docling": DoclingOptions}


@hookimpl
def add_options(parser: ArgumentParser) -> None:
    group = parser.add_argument_group("Docling Serve")
    group.add_argument(
        "--docling",
        dest="ocr_engine",
        action="store_const",
        const="docling",
        help="Use Docling Serve with the DCC word-box extension for OCR",
    )
    group.add_argument("--docling-url", metavar="URL", help="Docling Serve base URL")
    group.add_argument("--docling-preset", metavar="PRESET", help="Server OCR preset")
    group.add_argument(
        "--docling-timeout", metavar="SECONDS", type=float, help="HTTP request timeout"
    )


@hookimpl
def check_options(options: OcrOptions) -> None:
    if options.ocr_engine != "docling":
        return
    if options.pdf_renderer == "sandwich":
        raise BadArgsError("Docling requires --pdf-renderer auto or fpdf2")
    if options.rotate_pages or options.deskew:
        raise BadArgsError("Docling does not support --rotate-pages or --deskew")
    try:
        _ = options.docling
    except ValidationError as error:
        first_error = error.errors()[0]
        raise BadArgsError(
            f"Invalid Docling {first_error['loc'][0]}: {first_error['msg']}"
        ) from error


@hookimpl
def get_ocr_engine(options: OcrOptions | None) -> DoclingEngine | None:
    if options is not None and options.ocr_engine == "docling":
        return DoclingEngine()
    return None
