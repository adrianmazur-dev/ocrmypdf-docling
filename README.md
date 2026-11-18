# ocrmypdf-docling

An OCRmyPDF plugin that sends page images to Docling Serve and embeds the recognized words as a searchable text layer. It uses the [DCC word-box extension](https://github.com/DCC-BS/dcc-docling-serve#convert-api-the-words-of-each-page) to position individual words in the PDF.

For tables, the plugin uses Docling's row and column order when writing the PDF text layer and the plain-text sidecar. It uses DCC word positions and measures line height and baseline from the page image. The Docling response is used during conversion only.

## Run Docling Serve

Start the DCC image on the same machine for a CPU setup. It includes Docling Serve, the word-box extension, and the `pp-ocrv6` preset.

```sh
docker run --rm -p 127.0.0.1:5001:5001 \
  -e DOCLING_SERVE_ALLOW_EXTERNAL_PLUGINS=true \
  -e DOCLING_SERVE_ENG_LOC_NUM_WORKERS=1 \
  -e DOCLING_DEVICE=cpu \
  ghcr.io/dcc-bs/dcc-docling-serve-cpu:v1.38.2
```

Wait for `http://127.0.0.1:5001/health` to respond. For CUDA, use a [DCC CUDA image](https://github.com/DCC-BS/dcc-docling-serve#available-images) and configure GPU access on the server.

## Use the plugin

Install OCRmyPDF and the plugin in the same tool environment.

```sh
uv tool install --python 3.14 --with ocrmypdf-docling ocrmypdf
ocrmypdf --docling -l pol --sidecar output.txt input.pdf output.pdf
```

From this repository, install with `uv sync --locked` and run OCRmyPDF with `uv run`.

```sh
uv run ocrmypdf --docling -l pol --sidecar output.txt input.pdf output.pdf
```

For a remote deployment, specify its base URL. Presets must provide OCR line and word boxes through DCC.

```sh
uv run ocrmypdf --docling --docling-url https://docling.example.com \
  --docling-preset pp-ocrv6 --docling-timeout 120 -l pol input.pdf output.pdf
```

Set `DOCLING_SERVE_API_KEY` in the client environment if the server requires authentication. Each page image is sent to the configured server. `--jobs` controls how many pages OCRmyPDF can submit concurrently. Use the default renderer or `--pdf-renderer fpdf2`. Rotation and deskew should be handled before running this adapter.

The Python API accepts the same settings.

```python
import ocrmypdf

ocrmypdf.ocr(
    "input.pdf",
    "output.pdf",
    ocr_engine="docling",
    languages=["pol"],
    docling_url="http://127.0.0.1:5001",
)
```
