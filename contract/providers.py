from typing import Protocol, runtime_checkable

from .catalog import InfrastructureCatalogOptions
from .selection import SpawnOffering
from .types import UserLike


@runtime_checkable
class InfrastructureCatalogProvider(Protocol):
    """A protocol for providing an infrastructure catalog.

    The infrastructure spawner provides this; the course hub consumes it.
    """

    def get_infrastructure_catalog(self) -> InfrastructureCatalogOptions: ...


@runtime_checkable
class SpawnOfferingProvider(Protocol):
    """A protocol for providing the spawns a user is permitted to launch.

    The course hub provides this; the infrastructure spawner consumes it at
    spawn time to learn what a user may launch, per course/term.
    """

    def get_spawn_offerings(self, user: UserLike) -> list[SpawnOffering]: ...
