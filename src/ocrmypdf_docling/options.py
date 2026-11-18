from typing import Annotated

from pydantic import AnyHttpUrl, BaseModel, Field, StringConstraints, field_validator


class DoclingOptions(BaseModel):
    """Connection and OCR settings for Docling Serve."""

    url: AnyHttpUrl = AnyHttpUrl("http://127.0.0.1:5001")
    preset: Annotated[str, StringConstraints(strip_whitespace=True, min_length=1)] = (
        "pp-ocrv6"
    )
    timeout: float = Field(default=120.0, gt=0, allow_inf_nan=False)

    @field_validator("url")
    @classmethod
    def validate_base_url(cls, url: AnyHttpUrl) -> AnyHttpUrl:
        if any((url.query, url.fragment, url.username, url.password)):
            raise ValueError(
                "Use a base URL without credentials, a query, or a fragment"
            )
        return url
