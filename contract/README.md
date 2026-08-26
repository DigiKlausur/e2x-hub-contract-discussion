# `e2x_course_hub.contract`

The shared contract between the **e2x course hub** and the **infrastructure spawner**
(the JupyterHub Spawner extension that launches user containers).

This package contains only types and protocols — no I/O, no database, no JupyterHub or
RBAC imports. It depends on `pydantic` and the standard library only, so either side can
import it cheaply and safely.

## The two sides

|                       | Course hub                          | Infrastructure spawner                     |
|-----------------------|-------------------------------------|--------------------------------------------|
| Knows                 | courses, terms, users, roles (via `e2x_hub_rbac`), permissions | what can actually be run: image families/tags, resource tiers, profiles |
| Implements            | `SpawnOfferingProvider`             | `InfrastructureCatalogProvider`            |
| Consumes              | `InfrastructureCatalogProvider`     | `SpawnOfferingProvider`                    |
| Never does            | translates tiers/profiles to hardware | decides who is allowed to do what         |

The split is deliberate: **the hub owns authorization, the spawner owns infrastructure.**
They meet only through this contract.

Both sides receive the other's provider **by injection** (constructor/config). Neither
side imports the other's implementation.

## How a spawn works

```text
1.  hub ── get_infrastructure_catalog() ──→ spawner
      The hub fetches the catalog to constrain what it offers and to render the pick UI.

2.  spawner ── get_spawn_offerings(user) ──→ hub
      ← list[SpawnOffering]
      One offering per course/term the user may act in, each carrying the
      hub-assigned spawn role and any preset selection values.

3.  The user picks an offering and optionally refines image / tag / tier / profile.

4.  spawner: catalog.resolve(selection) → ResolvedSpawn
      Every default is applied, every reference is validated.

5.  spawner: start() translates the ResolvedSpawn to hardware and launches the container.
```

## Modules

| Module         | What's in it                                                                  |
|----------------|-------------------------------------------------------------------------------|
| `types.py`     | Shared primitives used across the other modules: `SpawnRole`, `UserLike`      |
| `catalog.py`   | The infrastructure catalog (what *can* be run) and `InfrastructureCatalogOptions.resolve()` |
| `selection.py` | The offer/selection layer (what a user *may* run, where, and the resolved result) |
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

In a `SpawnSelection`, **`None` means "use the catalog default"** (no image → default
family, no tag → default tag, no profile → default profile, no tier → default tier).
`resolve()` is the only place where that convention is materialized, and it validates
every reference along the way. The result is a fully concrete `ResolvedSpawn` — no
`None`s, no dangling names — or a typed `CatalogError`.

```python
try:
    resolved = catalog.resolve(selection)
except CatalogError as e:
    ...  # user-facing: unknown role / family / tag / profile / tier
```

The `assert_*` methods on the catalog and the option collections are pre-flight checks
for callers that want to validate before resolving.

## Selections and offerings — what a user *may* run

| Type             | Meaning                                                                                  |
|------------------|------------------------------------------------------------------------------------------|
| `ImageSelection` | An image family + optional tag                                                            |
| `SpawnSelection` | A (partial) spawn: role + optional image / tier / profile. `None` = default              |
| `CourseContext`  | Where: course + term (+ display name / description)                                       |
| `SpawnOffering`  | Where + what: one course/term the user may act in, with the hub-assigned selection. The unit returned by `get_spawn_offerings()` |
| `ResolvedSpawn`  | The fully concrete result of `resolve()` — what the spawner actually launches            |

> **Security note:** `SpawnSelection.spawn_role` is assigned by the hub from RBAC (a
> user is a student in one course, a grader in another). It is **authoritative** — the
> spawner must never present it as user-selectable or accept a user-supplied role.

## Errors

There are exactly two failure classes:

1. **Malformed catalog** → `pydantic.ValidationError` at construction time. Catalog data
   that doesn't fit the schema (including broken `default_*` references) fails fast when
   the catalog is loaded.
2. **Invalid selection** → a `CatalogError` subclass at `resolve()` / `assert_*` time.
   All of them are also `ValueError`s, and all are catchable as `CatalogError`:

| Exception                  | Raised when                                    |
|----------------------------|------------------------------------------------|
| `UnknownSpawnRoleError`    | the selection's role has no entry in the catalog |
| `UnknownImageFamilyError`  | the image family doesn't exist                 |
| `UnknownImageTagError`     | the tag doesn't exist for that family          |
| `UnknownProfileError`      | the profile doesn't exist for that role        |
| `UnknownResourceTierError` | the tier doesn't exist for that role           |

## `UserLike`

A minimal structural protocol — `username: str`, `groups: list[str]`. The spawner
adapts JupyterHub's `User` to it (`.name` → `username`, `.groups` → `groups`). Keep it
minimal: add an attribute only when the spawner actually needs it. Because it's
structural, any object with those attributes satisfies it — no import from
`e2x_hub_rbac` is required on either side.

## Rules for implementers

### Spawner side (infrastructure)

- Build the catalog so it covers **every** `SpawnRole` the hub may assign, with valid
  `default_*` entries.
- Implement `InfrastructureCatalogProvider`; expose the catalog immutably.
- At spawn time: adapt the JupyterHub `User` → `UserLike`, call `get_spawn_offerings()`,
  and render the pick UI from the offerings + catalog.
- Treat `spawn_role` as fixed. Let the user refine only image / tag / tier / profile,
  and only among values the offering and catalog allow.
- Always `catalog.resolve(selection)` before launching — don't hand-roll default application.
- Catch `CatalogError` for user-facing failures.

### Hub side

- Implement `SpawnOfferingProvider`; return one `SpawnOffering` per course/term the user
  may act in.
- Set `spawn_role` from `e2x_hub_rbac` — never from user input.
- Only reference profile / tier / image values that exist in the catalog (fetch it via
  the injected `InfrastructureCatalogProvider`), or leave the field `None` to let the
  spawner apply the default.
- Keep `e2x_course_hub/__init__.py` light: importing the contract must not pull in RBAC,
  database, or management code.

## Changing this contract

This package is a **stable API shared by two independently deployed components**.
Treat it accordingly:

- Adding optional fields or new types: generally safe.
- Renaming, removing, or re-typing anything: breaking — coordinate with the other side.
- Keep the package dependency-light (`pydantic` + stdlib only). If a new type needs hub
  or JupyterHub imports, it probably doesn't belong in the contract.
