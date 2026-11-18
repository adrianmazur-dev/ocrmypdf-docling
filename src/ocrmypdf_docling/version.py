from importlib.metadata import version


def plugin_version() -> str:
    return version("ocrmypdf-docling")
