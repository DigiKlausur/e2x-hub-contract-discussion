from pydantic import BaseModel, ConfigDict, Field

from .types import SpawnRole


class ImageSelection(BaseModel):
    """A selection of an image family and an optional tag."""

    model_config = ConfigDict(extra="forbid", frozen=True)
    family: str = Field(min_length=1)
    tag: str | None = None


class SpawnSelection(BaseModel):
    """A selection of spawn options, including spawn role, image selection, resource tier,
    and profile name."""

    model_config = ConfigDict(extra="forbid", frozen=True)
    spawn_role: SpawnRole
    image: ImageSelection | None = None
    resource_tier: str | None = None
    profile_name: str | None = None


class ResolvedSpawn(BaseModel):
    """A resolved spawn configuration, including spawn role, image family, tag, profile,
    and resource tier."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    spawn_role: SpawnRole
    family: str = Field(min_length=1)
    tag: str = Field(min_length=1)
    profile: str = Field(min_length=1)
    resource_tier: str = Field(min_length=1)


class CourseContext(BaseModel):
    """
    Represents the context of a specific course and term.
    """

    model_config = ConfigDict(extra="forbid", frozen=True)

    course_id: str = Field(min_length=1)
    term_id: str = Field(min_length=1)
    course_display_name: str = Field(min_length=1)
    course_description: str | None = None


class SpawnOffering(BaseModel):
    """
    Represents a spawn option for a user, including the course context and the spawn selection.
    """

    model_config = ConfigDict(extra="forbid", frozen=True)
    course_context: CourseContext
    selection: SpawnSelection
