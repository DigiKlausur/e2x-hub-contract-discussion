class CatalogError(ValueError):
    """Base class for catalog-related errors."""


class UnknownSpawnRoleError(CatalogError):
    """Raised when a spawn role is not found in the catalog."""

    def __init__(self, spawn_role: str):
        super().__init__(f"Spawn role '{spawn_role}' not found in the catalog.")


class UnknownProfileError(CatalogError):
    """Raised when a profile is not found in the catalog."""

    def __init__(self, profile_name: str):
        super().__init__(f"Profile '{profile_name}' not found in the catalog.")


class UnknownResourceTierError(CatalogError):
    """Raised when a resource tier is not found in the catalog."""

    def __init__(self, tier_name: str):
        super().__init__(f"Resource tier '{tier_name}' not found in the catalog.")


class UnknownImageFamilyError(CatalogError):
    """Raised when an image family is not found in the catalog."""

    def __init__(self, family_name: str):
        super().__init__(f"Image family '{family_name}' not found in the catalog.")


class UnknownImageTagError(CatalogError):
    """Raised when an image tag is not found in the catalog."""

    def __init__(self, family_name: str, tag: str):
        super().__init__(f"Image tag '{tag}' not found for family '{family_name}' in the catalog.")
