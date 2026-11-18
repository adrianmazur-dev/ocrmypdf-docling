from langcodes import standardize_tag

# OCRmyPDF also accepts Tesseract codes for scripts and historical languages.
_TESSERACT_TAGS = {
    "chi_sim": "zh-Hans",
    "chi_tra": "zh-Hant",
    "deu_latf": "de-Latf",
    "frk": "de-Latf",
    "jpn_vert": "ja",
    "kor_vert": "ko",
    "srp_latn": "sr-Latn",
    "uzb_cyrl": "uz-Cyrl",
}


def docling_language(code: str) -> str:
    """Translate an OCRmyPDF language code to a Docling Serve BCP 47 tag."""
    return standardize_tag(_TESSERACT_TAGS.get(code.lower(), code))
