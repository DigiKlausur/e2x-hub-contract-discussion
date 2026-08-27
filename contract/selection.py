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
    resource_tier_name: str | None = None
    profile_name: str | None = None


class CourseReference(BaseModel):
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
    Represents a spawn option for a user, including the course reference and the spawn selection.
    """

    model_config = ConfigDict(extra="forbid", frozen=True)
    course: CourseReference
    selection: SpawnSelection
