from enum import StrEnum
from typing import Protocol


class UserLike(Protocol):
    """A protocol representing a user-like object with a username and groups."""

    username: str
    groups: list[str]


class SpawnRole(StrEnum):
    """Enumeration of spawn roles for the e2x course hub."""

    STUDENT = "student"
    GRADER = "grader"
    GRADER_READONLY = "grader-readonly"
