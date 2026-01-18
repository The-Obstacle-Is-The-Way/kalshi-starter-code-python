"""Pydantic models for Exa Websets API."""

from __future__ import annotations

from datetime import datetime  # noqa: TC003
from enum import Enum
from typing import Any

from pydantic import BaseModel, ConfigDict, Field


class WebsetStatus(str, Enum):
    """Status of a Webset."""

    IDLE = "idle"
    PENDING = "pending"
    RUNNING = "running"
    PAUSED = "paused"


class WebsetSearchStatus(str, Enum):
    """Status of a Webset search."""

    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELED = "canceled"


class EntityType(str, Enum):
    """Type of entity in a Webset."""

    COMPANY = "company"
    PERSON = "person"
    ARTICLE = "article"
    RESEARCH_PAPER = "research_paper"
    CUSTOM = "custom"


class WebsetSource(BaseModel):
    """Reference to an import or webset source."""

    model_config = ConfigDict(frozen=True)

    source: str = Field(..., description="Source type: 'import' or 'webset'")
    id: str = Field(..., description="ID of the source")


class Entity(BaseModel):
    """Entity specification for Webset search."""

    model_config = ConfigDict(frozen=True)

    type: EntityType = Field(..., description="Type of entity")


class CreateCriterionParameters(BaseModel):
    """Parameters for creating a search criterion."""

    model_config = ConfigDict(frozen=True)

    definition: str = Field(..., min_length=1, max_length=500, description="Criterion definition")


class CreateWebsetSearchParameters(BaseModel):
    """Parameters for creating a Webset search."""

    model_config = ConfigDict(frozen=True)

    query: str = Field(
        ...,
        min_length=1,
        max_length=5000,
        description="Natural language search query",
    )
    count: int = Field(
        default=10,
        ge=1,
        description="Number of items to find",
    )
    entity: Entity | None = Field(
        default=None,
        description="Entity type (auto-detected if not provided)",
    )
    criteria: list[CreateCriterionParameters] | None = Field(
        default=None,
        min_length=1,
        max_length=5,
        description="Criteria for evaluation",
    )
    recall: bool | None = Field(
        default=None,
        description="Estimate total relevant results",
    )
    exclude: list[WebsetSource] | None = Field(
        default=None,
        description="Sources to exclude from search",
    )
    scope: list[dict[str, Any]] | None = Field(
        default=None,
        description="Limit search to specific sources",
    )


class CreateEnrichmentParameters(BaseModel):
    """Parameters for creating a Webset enrichment."""

    model_config = ConfigDict(frozen=True)

    # Simplified for Phase 1 - full schema is complex
    type: str = Field(..., description="Enrichment type")


class CreateWebsetParameters(BaseModel):
    """Parameters for creating a Webset."""

    model_config = ConfigDict(frozen=True)

    search: CreateWebsetSearchParameters | None = Field(
        default=None,
        description="Initial search for the Webset",
    )
    import_: list[WebsetSource] | None = Field(
        default=None,
        alias="import",
        description="Attach data from existing imports or websets",
    )
    enrichments: list[CreateEnrichmentParameters] | None = Field(
        default=None,
        description="Enrichments to extract additional data",
    )
    exclude: list[WebsetSource] | None = Field(
        default=None,
        description="Sources to exclude globally",
    )
    external_id: str | None = Field(
        default=None,
        alias="externalId",
        description="External identifier for integration",
    )
    title: str | None = Field(
        default=None,
        description="Webset title",
    )
    metadata: dict[str, str] | None = Field(
        default=None,
        description="Key-value pairs to associate with the Webset",
    )


class WebsetSearch(BaseModel):
    """A search performed on a Webset."""

    model_config = ConfigDict(frozen=True)

    id: str = Field(..., description="Search ID")
    object: str = Field(default="webset.search", description="Object type")
    status: WebsetSearchStatus = Field(..., description="Search status")
    query: str = Field(..., description="Search query")
    count: int = Field(..., description="Target number of results")
    found: int = Field(..., description="Number of items found")
    created_at: datetime = Field(..., alias="createdAt", description="Creation time")
    updated_at: datetime = Field(..., alias="updatedAt", description="Last update time")


class Import(BaseModel):
    """An import attached to a Webset."""

    model_config = ConfigDict(frozen=True)

    id: str = Field(..., description="Import ID")
    object: str = Field(default="import", description="Object type")
    status: str = Field(..., description="Import status")
    created_at: datetime = Field(..., alias="createdAt", description="Creation time")


class WebsetEnrichment(BaseModel):
    """An enrichment applied to Webset items."""

    model_config = ConfigDict(frozen=True)

    id: str = Field(..., description="Enrichment ID")
    object: str = Field(default="webset.enrichment", description="Object type")
    type: str = Field(..., description="Enrichment type")
    status: str = Field(..., description="Enrichment status")


class Monitor(BaseModel):
    """A monitor for continuous Webset updates."""

    model_config = ConfigDict(frozen=True)

    id: str = Field(..., description="Monitor ID")
    object: str = Field(default="monitor", description="Object type")
    status: str = Field(..., description="Monitor status")


class Webset(BaseModel):
    """A Webset collection of web data."""

    model_config = ConfigDict(frozen=True)

    id: str = Field(..., description="Webset ID")
    object: str = Field(default="webset", description="Object type")
    status: WebsetStatus = Field(..., description="Webset status")
    external_id: str | None = Field(None, alias="externalId", description="External ID")
    title: str | None = Field(None, description="Webset title")
    searches: list[WebsetSearch] = Field(default_factory=list, description="Searches performed")
    imports: list[Import] = Field(default_factory=list, description="Imports performed")
    enrichments: list[WebsetEnrichment] = Field(
        default_factory=list, description="Enrichments applied"
    )
    monitors: list[Monitor] = Field(default_factory=list, description="Monitors active")
    excludes: list[WebsetSource] | None = Field(None, description="Global exclude sources")
    metadata: dict[str, str] = Field(default_factory=dict, description="User metadata")
    created_at: datetime = Field(..., alias="createdAt", description="Creation time")
    updated_at: datetime = Field(..., alias="updatedAt", description="Last update time")


class GetWebsetResponse(BaseModel):
    """Response from GET /v0/websets/{id}."""

    model_config = ConfigDict(frozen=True)

    # The API returns the Webset object directly
    # This is a wrapper if needed, but typically GET returns Webset directly
    id: str
    object: str
    status: WebsetStatus
    external_id: str | None = Field(None, alias="externalId")
    title: str | None
    searches: list[WebsetSearch]
    imports: list[Import]
    enrichments: list[WebsetEnrichment]
    monitors: list[Monitor]
    excludes: list[WebsetSource] | None
    metadata: dict[str, str]
    created_at: datetime = Field(..., alias="createdAt")
    updated_at: datetime = Field(..., alias="updatedAt")


class WebsetItemProperties(BaseModel):
    """Properties extracted for a Webset item."""

    model_config = ConfigDict(frozen=True)

    # Simplified for Phase 1 - actual properties vary by entity type
    pass


class WebsetItemEvaluation(BaseModel):
    """Evaluation result for a Webset item."""

    model_config = ConfigDict(frozen=True)

    criterion_id: str = Field(..., alias="criterionId", description="Criterion ID")
    result: bool = Field(..., description="Whether criterion was met")
    explanation: str | None = Field(None, description="Explanation of result")


class WebsetItem(BaseModel):
    """An item in a Webset."""

    model_config = ConfigDict(frozen=True)

    id: str = Field(..., description="Item ID")
    object: str = Field(default="webset.item", description="Object type")
    webset_id: str = Field(..., alias="websetId", description="Parent Webset ID")
    entity_type: EntityType = Field(..., alias="entityType", description="Entity type")
    url: str = Field(..., description="Item URL")
    title: str | None = Field(None, description="Item title")
    properties: dict[str, Any] = Field(
        default_factory=dict, description="Entity-specific properties"
    )
    evaluations: list[WebsetItemEvaluation] = Field(
        default_factory=list, description="Criterion evaluations"
    )
    enrichments: dict[str, Any] = Field(default_factory=dict, description="Enrichment results")
    metadata: dict[str, str] = Field(default_factory=dict, description="User metadata")
    created_at: datetime = Field(..., alias="createdAt", description="Creation time")
    updated_at: datetime = Field(..., alias="updatedAt", description="Last update time")


class ListWebsetItemResponse(BaseModel):
    """Response from GET /v0/websets/{webset}/items."""

    model_config = ConfigDict(frozen=True)

    object: str = Field(default="list", description="Object type")
    data: list[WebsetItem] = Field(..., description="List of items")
    has_more: bool = Field(False, alias="hasMore", description="More items available")
    next_cursor: str | None = Field(None, alias="nextCursor", description="Pagination cursor")


class PreviewWebsetParameters(BaseModel):
    """Parameters for previewing a Webset."""

    model_config = ConfigDict(frozen=True)

    search: CreateWebsetSearchParameters = Field(..., description="Search to preview")


class WebsetItemPreview(BaseModel):
    """Preview of a Webset item."""

    model_config = ConfigDict(frozen=True)

    url: str = Field(..., description="Item URL")
    title: str | None = Field(None, description="Item title")
    entity_type: EntityType = Field(..., alias="entityType", description="Entity type")
    evaluations: list[WebsetItemEvaluation] = Field(
        default_factory=list, description="Criterion evaluations"
    )


class PreviewWebsetResponse(BaseModel):
    """Response from POST /v0/websets/preview."""

    model_config = ConfigDict(frozen=True)

    object: str = Field(default="list", description="Object type")
    data: list[WebsetItemPreview] = Field(..., description="Preview items")
