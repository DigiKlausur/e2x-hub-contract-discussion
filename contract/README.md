# `e2x_course_hub.contract`

The shared contract between the **e2x course hub** and **the spawner** (the JupyterHub
Spawner that launches user containers).

## The two sides

|               | Course hub                                                        | Spawner                                          |
|---------------|-------------------------------------------------------------------|--------------------------------------------------|
| Knows         | courses, terms, users, roles (via `e2x_hub_rbac`), permissions, and the selection configured per course/term | what can actually be run: image families/tags, resource tiers, profiles |
| Implements    | `SpawnOfferingProvider`                                           | `InfrastructureCatalogProvider`                  |
| Consumes      | `InfrastructureCatalogProvider`                                   | `SpawnOfferingProvider`                          |
| Never does    | translates a selection to hardware                                | decides who is allowed to do what                |

The split is deliberate: **the course hub owns authorization and course configuration; the
spawner owns the runtime.** They meet only through this contract.

## Who decides what

| Decision                                             | Made by                                    | When                 |
|------------------------------------------------------|--------------------------------------------|----------------------|
| Which image / tier / profile a course/term uses      | A course manager (like instructor, owner, TA), via the course hub (gated by permission) | Course configuration |
| Which courses/terms a user may launch, and their role| The course hub (via `e2x_hub_rbac`)        | Spawn time           |
| Which course/term to launch                          | The user                                   | Spawn time           |
| How a selection becomes a running container          | The spawner (catalog + translation)        | Spawn time           |

The selection is **not** chosen by the spawning user. It is configured per course/term
by whoever has the permission to do so, stored by the hub, and handed to the spawner at
spawn time. The user's only spawn-time choice is *which course/term to launch* and *which spawn role within that course/term*.

## How a spawn works

```text
1.  JupyterHub ── provides the current User
2.  spawner ── get_spawn_offerings(user) ──→ e2x-course-hub
      ← list[SpawnOffering]
      One offering per course/term the user may launch, each carrying the
      user's role in it and the selection configured for that course/term.
3.  spawner ── use list[SpawnOffering] to render the spawn page and present the UI where a user can pick their course/term.

4.  The user picks which offering (course/term) to launch.

5.  spawner: catalog.resolve(selection) → ResolvedSpawn
      Any selection field left unset is filled from the catalog default;
      every reference is validated.

6.  spawner: start() translates the ResolvedSpawn to hardware and launches the container.
```

## Modules

| Module         | What's in it                                                                  |
|----------------|-------------------------------------------------------------------------------|
| `types.py`     | Shared primitives used across the other modules: `SpawnRole`, `UserLike`      |
| `catalog.py`   | The infrastructure catalog (what *can* be run) and `InfrastructureCatalogOptions.resolve()` |
| `selection.py` | The offer/selection layer (what a user *may* launch, where, and the resolved result) |
| `providers.py` | The two protocols that define the boundary                                    |
| `errors.py`    | `CatalogError` and the typed lookup errors                                    |

Import from the package root — the submodules are an implementation detail:

```python
from e2x_course_hub.contract import (
    InfrastructureCatalogOptions,
    SpawnOffering,
    SpawnSelection,
    ResolvedSpawn,
    SpawnRole,
    CatalogError,
)
```

## The catalog — what *can* be run

"Option" in this package means **an available value** (a menu item): a `ProfileOption`
is a profile that exists, a `ResourceTierOption` is a tier that exists, and so on.

```text
InfrastructureCatalogOptions
├── image_family_options: ImageFamilyOptions
│   ├── default_family: str
│   └── families: {name → ImageFamilyOption}
│       ├── display_name, description
│       ├── default_tag: str
│       └── tags: {tag → ImageTagInfo(status, message?)}
└── spawn_role_options: {SpawnRole → SpawnRoleOptions}
    ├── profile_options
    │   ├── default_profile: str
    │   └── profiles: {name → ProfileOption(display_name, description?)}
    └── resource_tier_options
        ├── default_tier: str
        └── tiers: {name → ResourceTierOption(display_name, description, warning?, metadata?)}
```

Guarantees, enforced at construction time:

- Every `default_*` refers to an entry that exists — a typo fails the load, with a
  message listing the valid keys.
- All models are `frozen` and `extra="forbid"` — immutable, and unknown keys are rejected.

### `resolve()` — the single entry point

`InfrastructureCatalogOptions.resolve(selection: SpawnSelection) -> ResolvedSpawn`

In a `SpawnSelection`, **`None` means "not configured → use the catalog default"** (no
image → default family, no tag → default tag, no profile → default profile, no tier →
default tier). A course/term config often sets only some of these (e.g., the image but
not the tier); `resolve()` fills the rest and validates every reference. It is the only
place where that convention is materialized. The result is a fully concrete
`ResolvedSpawn` — no `None`s, no dangling names — or a typed `CatalogError`.

```python
try:
    resolved = catalog.resolve(selection)
except CatalogError as e:
    ...  # user-facing: unknown role / family / tag / profile / tier
```

The `assert_*` methods on the catalog and the option collections are pre-flight checks
for callers that want to validate before resolving.

## Selections and offerings — what a user *may* launch

| Type             | Meaning                                                                                  |
|------------------|------------------------------------------------------------------------------------------|
| `ImageSelection` | An image family + optional tag                                                            |
| `SpawnSelection` | The selection configured for a course/term: role + image / tier / profile. A field left `None` means "not configured → catalog default" |
| `CourseContext`  | Where: course + term (+ display name / description)                                       |
| `SpawnOffering`  | A course/term the user may launch, carrying their role in it and its configured selection. The unit returned by `get_spawn_offerings()` |
| `ResolvedSpawn`  | The fully concrete result of `resolve()` — what the spawner actually launches            |

> **Security note:** `SpawnSelection.spawn_role` is assigned by the hub from RBAC (a
> user is a student in one course, a grader in another). It is **authoritative** — the
> spawner must never present it as user-selectable or accept a user-supplied role. The
> configured selection is authoritative too: the user chooses the course/term, not the
> image/tier/profile.

## Errors

There are exactly two failure classes:

1. **Malformed catalog** → `pydantic.ValidationError` at construction time. Catalog data
   that doesn't fit the schema (including broken `default_*` references) fails fast when
   the catalog is loaded.
2. **Invalid selection** → a `CatalogError` subclass at `resolve()` / `assert_*` time.
   All of them are also `ValueError`s, and all are catchable as `CatalogError`:

| Exception                  | Raised when                                     |
|----------------------------|-------------------------------------------------|
| `UnknownSpawnRoleError`    | the selection's role has no entry in the catalog |
| `UnknownImageFamilyError`  | the image family doesn't exist                  |
| `UnknownImageTagError`     | the tag doesn't exist for that family           |
| `UnknownProfileError`      | the profile doesn't exist for that role         |
| `UnknownResourceTierError` | the tier doesn't exist for that role            |

## `UserLike`

A minimal structural protocol — `username: str`, `groups: list[str]`. The spawner
adapts JupyterHub's `User` to it (`.name` → `username`, `.groups` → `groups`). Keep it
minimal: add an attribute only when the spawner actually needs it. Because it's
structural, any object with those attributes satisfies it — no import from
`e2x_hub_rbac` is required on either side.

