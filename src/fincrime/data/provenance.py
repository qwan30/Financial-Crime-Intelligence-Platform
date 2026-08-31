from __future__ import annotations

from hashlib import sha256
from pathlib import Path
from typing import Annotated

from pydantic import (
    AwareDatetime,
    BaseModel,
    ConfigDict,
    Field,
    HttpUrl,
    StringConstraints,
    field_validator,
)

NonBlank = Annotated[str, StringConstraints(strip_whitespace=True, min_length=1)]
Hash = Annotated[str, StringConstraints(pattern=r"^[0-9a-f]{64}$")]


class SourceManifest(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")

    source_id: NonBlank
    source_url: HttpUrl
    revision: NonBlank
    license: NonBlank
    retrieved_at: AwareDatetime
    raw_sha256: Hash
    schema_sha256: Hash
    extraction_selector: NonBlank
    intended_use: NonBlank
    prohibited_claims: tuple[NonBlank, ...]
    limitations: tuple[NonBlank, ...]

    @field_validator("source_url")
    @classmethod
    def require_https(cls, value: HttpUrl) -> HttpUrl:
        if value.scheme != "https":
            raise ValueError("source_url must use HTTPS")
        return value


class DerivedArtifactManifest(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")

    source_id: NonBlank
    parent_raw_sha256: Hash
    adapter_name: NonBlank
    adapter_version: NonBlank
    conversion_parameters: tuple[tuple[NonBlank, NonBlank], ...]
    output_sha256: Hash
    row_count: int = Field(ge=0)
    public_columns: tuple[NonBlank, ...]


def sha256_header(header: str) -> str:
    return sha256(header.encode("utf-8")).hexdigest()


def sha256_file(path: Path) -> str:
    digest = sha256()
    with path.open("rb") as source:
        for chunk in iter(lambda: source.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()
