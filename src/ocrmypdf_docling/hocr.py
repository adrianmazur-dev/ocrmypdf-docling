from html import escape

from ocrmypdf import OcrClass, OcrElement


def to_hocr(page: OcrElement) -> str:
    """Serialize a page containing OCR lines and words as hOCR."""
    return (
        '<?xml version="1.0" encoding="UTF-8"?>\n'
        '<html xmlns="http://www.w3.org/1999/xhtml"><head><title></title>'
        '<meta name="ocr-system" content="OCRmyPDF Docling Serve"/>'
        '<meta name="ocr-capabilities" content="ocr_page ocr_par ocr_line ocrx_word"/>'
        f"</head><body>{_element(page)}</body></html>\n"
    )


def _element(element: OcrElement) -> str:
    is_page = element.ocr_class == OcrClass.PAGE
    tag = "div" if is_page else "span"
    box = element.bbox
    if box is None:
        raise ValueError("hOCR elements require a bounding box")
    title = f"bbox {round(box.left)} {round(box.top)} {round(box.right)} {round(box.bottom)}"
    if is_page:
        title += f"; ppageno {element.page_number or 0}"
        if element.dpi is not None:
            dpi = round(element.dpi)
            title += f"; scan_res {dpi} {dpi}"
    if element.confidence is not None:
        title += f"; x_wconf {round(element.confidence * 100)}"
    if element.baseline is not None:
        title += f"; baseline {element.baseline.slope:.4f} {round(element.baseline.intercept)}"
    content = (
        " ".join(map(_element, element.children))
        if element.children
        else escape(element.text)
    )
    if is_page and element.children:
        content = f'<p class="ocr_par">{content}</p>'
    return f'<{tag} class="{element.ocr_class}" title="{title}">{content}</{tag}>'
