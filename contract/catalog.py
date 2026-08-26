from typing import Self

from pydantic import BaseModel, ConfigDict, Field, model_validator

from .errors import (
    UnknownImageFamilyError,
    UnknownImageTagError,
    UnknownProfileError,
    UnknownResourceTierError,
    UnknownSpawnRoleError,
)
from .selection import ImageSelection, ResolvedSpawn, SpawnSelection
from .types import SpawnRole


class ProfileOption(BaseModel):
    """A profile option for a specific spawn role."""

    model_config = ConfigDict(extra="forbid", frozen=True)
    display_name: str = Field(min_length=1)
    description: str | None = None


class ProfileOptions(BaseModel):
    """A collection of profile options for a specific spawn role."""

    model_config = ConfigDict(extra="forbid", frozen=True)
    default_profile: str = Field(min_length=1)
    profiles: dict[str, ProfileOption]

    @model_validator(mode="after")
    def _default_profile_must_exist(self) -> Self:
        if self.default_profile not in self.profiles:
            raise ValueError(
                f"default_profile '{self.default_profile}' not in profiles: "
                f"{list(self.profiles.keys())}"
            )
        return self

    def assert_profile_exists(self, profile_name: str) -> None:
        if profile_name not in self.profiles:
            raise UnknownProfileError(profile_name)


class ResourceTierOption(BaseModel):
    """A resource tier option for a specific spawn role."""

    model_config = ConfigDict(extra="forbid", frozen=True)
    display_name: str = Field(min_length=1)
    description: str = Field(min_length=1)
    warning: str | None = None
    metadata: dict[str, str] | None = None


class ResourceTierOptions(BaseModel):
    """A collection of resource tier options for a specific spawn role."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    default_tier: str = Field(min_length=1)
    tiers: dict[str, ResourceTierOption]

    @model_validator(mode="after")
    def _default_tier_must_exist(self) -> Self:
        if self.default_tier not in self.tiers:
            raise ValueError(
                f"default_tier '{self.default_tier}' not in tiers: {list(self.tiers.keys())}"
            )
        return self

    def assert_tier_exists(self, tier_name: str) -> None:
        if tier_name not in self.tiers:
            raise UnknownResourceTierError(tier_name)


class SpawnRoleOptions(BaseModel):
    """Options for a specific spawn role, including profiles and resource tiers."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    profile_options: ProfileOptions
    resource_tier_options: ResourceTierOptions


class ImageTagInfo(BaseModel):
    """Information about a specific image tag."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    status: str
    message: str | None = None


class ImageFamilyOption(BaseModel):
    """An option for a specific image family."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    display_name: str = Field(min_length=1)
    description: str = Field(min_length=1)
    default_tag: str = Field(min_length=1)
    tags: dict[str, ImageTagInfo]

    @model_validator(mode="after")
    def _default_tag_must_exist(self) -> Self:
        if self.default_tag not in self.tags:
            raise ValueError(
                f"default_tag '{self.default_tag}' not in tags: {list(self.tags.keys())}"
            )
        return self


class ImageFamilyOptions(BaseModel):
    """A collection of image family options."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    default_family: str = Field(min_length=1)
    families: dict[str, ImageFamilyOption]

    @model_validator(mode="after")
    def _default_family_must_exist(self) -> Self:
        if self.default_family not in self.families:
            raise ValueError(
                f"default_family '{self.default_family}' not in families: "
                f"{list(self.families.keys())}"
            )
        return self

    def assert_family_and_tag_exists(self, family_name: str, tag: str | None) -> None:
        if family_name not in self.families:
            raise UnknownImageFamilyError(family_name=family_name)
        if tag is None:
            return  # No tag specified, nothing to check
        if tag not in self.families[family_name].tags:
            raise UnknownImageTagError(family_name=family_name, tag=tag)


class InfrastructureCatalogOptions(BaseModel):
    """The complete infrastructure catalog, including image families and spawn role options."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    image_family_options: ImageFamilyOptions
    spawn_role_options: dict[SpawnRole, SpawnRoleOptions]

    def resolve(self, selection: SpawnSelection) -> ResolvedSpawn:
        role_opts = self.spawn_role_options.get(selection.spawn_role)
        if role_opts is None:
            raise UnknownSpawnRoleError(selection.spawn_role)
        image = selection.image or ImageSelection(family=self.image_family_options.default_family)
        family_opt = self.image_family_options.families.get(image.family)
        if family_opt is None:
            raise UnknownImageFamilyError(image.family)
        if image.tag is not None and image.tag not in family_opt.tags:
            raise UnknownImageTagError(image.family, image.tag)
        profile = selection.profile_name or role_opts.profile_options.default_profile
        role_opts.profile_options.assert_profile_exists(profile)

        tier = selection.resource_tier or role_opts.resource_tier_options.default_tier
        role_opts.resource_tier_options.assert_tier_exists(tier)
        return ResolvedSpawn(
            spawn_role=selection.spawn_role,
            family=image.family,
            tag=image.tag or family_opt.default_tag,
            profile=profile,
            resource_tier=tier,
        )

    def assert_image_selection_exists(self, family_name: str, tag: str | None = None) -> None:
        self.image_family_options.assert_family_and_tag_exists(family_name, tag)

    def assert_profile_exists(self, spawn_role: SpawnRole, profile_name: str) -> None:
        if spawn_role not in self.spawn_role_options:
            raise UnknownSpawnRoleError(spawn_role)
        self.spawn_role_options[spawn_role].profile_options.assert_profile_exists(profile_name)

    def assert_resource_tier_exists(self, spawn_role: SpawnRole, tier_name: str) -> None:
        if spawn_role not in self.spawn_role_options:
            raise UnknownSpawnRoleError(spawn_role)
        self.spawn_role_options[spawn_role].resource_tier_options.assert_tier_exists(tier_name)
