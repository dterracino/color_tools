# Post-7.0 import/export update

## Status

Post-7.0 work in progress. The initial format-neutral transfer/base-contract,
user-color round-trip, and user-filament round-trip phases are implemented:

- `FilamentMetadata` and `FilamentExportData` carry collection metadata,
  ownership IDs, format properties, and ordered filament records.
- `FilamentImporter` shares path, dependency, availability, and detection
  behavior with `PaletteImporter` without requiring palette parsing hooks.
- Exporters accept `FilamentExportData` through `export_filament_data()` and
  fall back to existing filament export when they do not consume metadata.
- The registered `user_colors` importer reads the strict `name`/`hex` schema
  into `PaletteExportData` and recalculates every derived value.
- `UserColorsExporter` provides read-only planning, explicit conflict policy,
  structured changes, stale-plan protection, prospective validation, atomic
  data replacement, and sidecar refresh.
- Palette and filament import formats use separate typed registries backed by
  shared registration, listing, extension, and content-detection logic.
- The registered `user_filaments` importer reads the strict user schema into
  `FilamentExportData`; `UserFilamentsExporter` applies the same stateful safety
  contract using stable IDs as the sole replacement key.

External filament-format importers and independent ownership transfer remain
pending.

## Motivation

At the start of this update, the import and export systems were not symmetric:

- Exporters could export raw `ColorRecord` lists, `FilamentRecord` lists, and
  metadata-bearing `PaletteExportData` values.
- Importers only imported color palettes. `PaletteImporter.import_palette()`
  returned `PaletteExportData`.
- There was no filament-import contract, no `FilamentExportData` equivalent,
  and no HueForge filament importer.
- Neither framework provided a supported path for merging imported records
  into `user-colors.json` or `user-filaments.json`.
- `owned-filaments.json` is separate inventory state and is not represented by
  `FilamentRecord`.

Palette import already supports useful format conversion:

```text
external palette
    -> palette importer
    -> PaletteExportData
    -> palette exporter
    -> another external palette format
```

Filaments should support the same in-memory conversion pattern. User-data
persistence can then be added as a separate destination rather than coupling
every external importer directly to Color Tools' JSON files.

## Proposed separation of responsibilities

The preferred architecture has three stages:

```text
external file
    -> format importer
    -> validated in-memory transfer data
    -> ordinary format exporter OR user-data exporter
```

### 1. Format importers

Format importers should only:

- recognize and parse one external format;
- validate values required by that format;
- normalize them into Color Tools records or import entries;
- preserve relevant format information needed by the next stage; and
- report unsupported or lossy fields.

They should not choose merge policy, edit user files, regenerate integrity
sidecars, or update the installed package data directory.

### 2. In-memory transfer data

Transfer objects allow imported data to be inspected, transformed, filtered,
or sent to another exporter without writing anything.

`PaletteExportData` already fills this role for color palettes. The filament
side should add the symmetric `FilamentExportData` model. Importers return
these objects and exporters accept them, so the same data can move from one
format to another without either endpoint knowing about the other.

The agreed model mirrors `PaletteExportData`:

```python
@dataclass(slots=True)
class FilamentExportData:
    filaments: list[FilamentRecord]
    metadata: FilamentMetadata = field(
        default_factory=FilamentMetadata
    )
```

`FilamentMetadata` mirrors the broadly useful parts of `PaletteMetadata` while
omitting palette-specific presentation fields such as `columns`:

```python
@dataclass(slots=True)
class FilamentMetadata:
    name: str = ""
    author: str = ""
    description: str = ""
    tags: tuple[str, ...] = ()
    owned_filament_ids: tuple[str, ...] = ()
    properties: dict[str, Any] = field(default_factory=dict)
```

`owned_filament_ids` describes inventory state associated with the collection,
not an intrinsic property of any `FilamentRecord`. The general `properties`
mapping provides the same extension point as `PaletteMetadata`. An importer may
use it for verified format-specific information, such as external identifier
mappings needed for a loss-aware round trip, without adding those fields to the
core record model.

For backward compatibility, the existing `export_filaments(list)` operation
can remain. A symmetric `export_filament_data(FilamentExportData)` operation
can fall back to exporting `.filaments` when the destination does not use the
supplemental information, just as `export_palette(PaletteExportData)` falls
back to ordinary color export when metadata is unsupported.

This stable interchange model is intentionally independent of HueForge. A
future filament-manager adapter should only need to translate its external
schema to and from `FilamentExportData`; it should not require another core
record type or a direct dependency on any other format adapter.

### 3. User-data persistence

Writing or merging into user data has materially different behavior from
serializing a selected list to an output format. It requires:

- loading existing state;
- reconciling imported records against core and user records;
- detecting conflicts and ambiguous matches;
- applying an explicit merge policy;
- reporting operation-specific additions, updates, skips, and conflicts;
- validating the complete prospective document;
- writing atomically; and
- regenerating any integrity sidecar defined for the destination.

`user-colors.json` and `user-filaments.json` currently have sidecars.
`owned-filaments.json` does not, because it is mutable inventory state. This
plan should not add an ownership sidecar unless the broader integrity policy is
changed together with every existing ownership-writing path.

The user-data destinations are exporters because they consume the same transfer
objects, but their stateful contract is intentionally separate from the current
stateless exporter registry:

- `UserColorsExporter` accepts `PaletteExportData` and targets
  `user-colors.json`.
- `UserFilamentsExporter` accepts `FilamentExportData` and targets
  `user-filaments.json`.
- `OwnedFilamentsExporter`, or an explicitly ownership-aware filament export
  operation, targets `owned-filaments.json`.

These are state-aware exporters rather than simple serialization exporters.
Internally, they should delegate reconciliation, planning, and atomic
persistence to focused helpers so the exporter classes do not become
monolithic. That is an implementation separation, not a separate public
concept. `UserColorsExporter` establishes this direct `plan()`/`apply()`
pattern. Adding stateful classes to a registry should wait until the registry
can expose that contract without implying that ordinary path-returning export
methods are safe or supported.

The workflow remains modular:

```python
imported = hueforge_importer.import_filaments("library.json")
exporter = get_exporter("user_filaments")
plan = exporter.plan_filament_data(imported)
exporter.apply(plan)
```

A CLI command may orchestrate those steps for convenience without making the
format importer depend on the user-data exporter.

Catalog persistence and ownership persistence are separate workflows. A
catalog importer/exporter operation writes `user-filaments.json` only. An
ownership operation runs independently against the effective catalog and
writes `owned-filaments.json` only. A source format that contains both kinds of
data may support both operations, but the catalog import must not implicitly
change inventory state.

## Filament transfer model requirements

A plain `list[FilamentRecord]` is sufficient for format-to-format conversion,
but it cannot fully represent a HueForge import. A HueForge entry also has:

- an `Owned` flag;
- an external UUID;
- no Color Tools `finish` field; and
- no guaranteed Color Tools filament ID.

The parser therefore needs to retain import-only information so either the
catalog or ownership workflow can consume it. Two reasonable shapes are:

1. A filament collection plus separate ownership and external-identity maps.
2. A list of import entries, each containing a `FilamentRecord` candidate,
   optional ownership, and optional external identifier.

The second shape avoids relying on list indexes and keeps format-specific
identity associated with the record it describes. `FilamentExportData` can
expose its ordered `.filaments` list to ordinary exporters. Any ownership view
derived from the same source remains optional transfer information; applying
that view is a separate operation after catalog import.

This metadata must not be added to `FilamentRecord` merely to support import.
Ownership is user inventory state, and an external UUID is provenance from a
particular format; neither is intrinsic filament catalog data.

## HueForge import considerations

A first filament importer should likely target HueForge because Color Tools
already exports that format and its data maps well to the existing filament
model:

| HueForge field | Color Tools interpretation |
| --- | --- |
| `Brand` | `maker` |
| `Name` | `color` |
| `Color` | `hex` |
| `Type` | `type` |
| `Transmissivity` | `td_value` |
| `Owned` | inventory state, not a `FilamentRecord` field |
| `uuid` | external identity retained during reconciliation when needed |

`finish` would normally be `None` unless a future verified format rule provides
it. The importer must not guess finishes by splitting names or material types.

HueForge export UUIDs are deterministic UUIDv5 values derived from Color Tools
filament IDs. That operation is intentionally one-way: an arbitrary UUID, or
even a UUID previously produced by Color Tools, cannot be decoded back into
the original filament ID. Import therefore needs an explicit ID strategy.
When retaining the external UUID is necessary, the importer can store a
record-ID-to-UUID mapping in `FilamentMetadata.properties` rather than adding a
HueForge-specific field to `FilamentRecord`.

Recommended catalog reconciliation order:

1. Match an imported entry to a known core or user record using verified,
   normalized identity fields.
2. If exactly one existing record matches, reuse its Color Tools ID and do not
   create a duplicate user filament.
3. If no record matches, propose a deterministic new Color Tools ID and report
   it before writing.
4. If multiple records match, report ambiguity and require caller input rather
   than guessing.

Catalog reconciliation never updates `owned-filaments.json`. If the caller
also wants to import ownership from the HueForge file, it runs the independent
ownership operation afterward. That operation resolves selected filament
information against the now-current merged catalog and writes only IDs that
resolve unambiguously.

The exact identity key must be decided and tested. Maker, material type,
finish, color name, and normalized compound hex are all relevant. RGB alone is
not a safe filament identity because distinct products frequently share an
effective color.

## User-data destinations

### `user-colors.json`

`UserColorsExporter` should accept `PaletteExportData` or an ordered color list
and write only the authoritative user-color schema. Derived values should be
normalized through the canonical Color Tools conversion and formatting
functions rather than trusted from arbitrary input.

Conflict reporting should distinguish at least:

- the same normalized name;
- the same RGB under a different name; and
- an exact duplicate.

The caller should choose whether a conflict is skipped or replaces the
existing user record. Core data must remain read-only.

### `user-filaments.json`

`UserFilamentsExporter` should accept `FilamentExportData` and emit only
supported source fields:

- `id`
- `maker`
- `type`
- `finish`
- `color`
- `hex`
- `td_value`
- `other_names`

It should never serialize derived runtime fields such as RGB, LAB, source, or
swatch bytes. Imported records without a usable ID must receive a reviewed,
deterministic ID before they can participate in ownership tracking or stable
HueForge export.

Conflict reporting should distinguish exact duplicates, same-ID differences,
and likely identity matches with changed color or TD values. A color match by
itself must not silently replace a filament.

### `owned-filaments.json`

Ownership import/export is an independent reconciliation operation, not an
intrinsic filament-record field and not a side effect of catalog import. The
operation accepts an external owned-filament selection, resolves it against the
current merged Color Tools catalog, and merges the resulting IDs with the
existing `owned_filaments` list.

The current runtime contract is also ID-based. A user override retains the
system filament's ID, so an existing ownership reference follows the effective
replacement record automatically. A new record in `user-filaments.json` can be
owned by adding its new ID. `--validate-user-files` validates the ownership
schema and resolves every owned ID against the fully merged system-plus-user
catalog.

For additive ownership imports, an external `Owned: false` value means only
that the record is not selected for the ownership operation; it must not remove
an existing local ownership reference. Removing ownership requires an explicit
inventory synchronization or replacement operation.

For external inventory systems, results should be divided into:

- matched and already owned;
- matched and newly marked owned;
- unmatched entries; and
- ambiguous entries requiring review.

The ownership operation never creates or modifies filament records. When an
external library contains filaments that are not yet present, run its catalog
import first and then rerun ownership resolution against the updated catalog.
This contract lets the same ownership operation support HueForge and future
filament-management systems without coupling them to user-filament writes.

Unknown external identifiers must not be written directly into
`owned-filaments.json`, because the current ownership API expects IDs that can
resolve against the Color Tools filament catalog.

## Merge and safety contract

User-data writes should follow the safe import-tooling pattern established for
the 7.0 data imports:

- Planning or dry-run is the default.
- Applying changes requires an explicit action such as `apply=True` or
  `--apply`.
- The plan identifies exact input files, target files, record counts, merge
  decisions, warnings, and conflicts.
- The state-aware exporter refuses unresolved conflicts unless the caller supplies a
  documented policy.
- Existing files are not modified until the complete proposed state validates.
- Writes use temporary files and atomic replacement.
- Output is deterministic and idempotent.
- A corresponding sidecar hash, when the destination participates in user-file
  integrity verification, is regenerated only after a successful write.
- Core `colors.json`, `filaments.json`, and maker synonyms are never targets of
  this user workflow.

Suggested explicit merge policies are `add`, `skip`, `update`, and `replace`.
Their semantics must be defined separately for colors, filaments, and owned
IDs; one generic policy should not conceal different identity rules.

Each operation validates and atomically replaces only its own destination.
Catalog import updates `user-filaments.json` and its sidecar. Ownership import
updates `owned-filaments.json`, which intentionally has no sidecar. Running the
catalog operation first makes interruption safe: a failure before ownership
import leaves valid user filaments that are simply not yet marked owned, and
the independent ownership operation can be rerun.

## Result and reporting objects

Normal format exporters can continue returning the destination path. Stateful
user-data operations need a structured result that can support both Python and
CLI callers. A result should report:

- source and destination paths;
- dry-run or applied status;
- parsed, accepted, added, updated, skipped, and rejected counts;
- ownership additions and already-owned counts for ownership operations;
- conflicts, ambiguities, and warnings;
- generated or reused Color Tools IDs; and
- whether each data file and sidecar was written.

This richer result belongs to state-aware export operations. It does not
require changing every existing exporter operation to return a result object;
the new planning/apply contract can be introduced alongside the existing
path-returning methods.

## Importer framework evolution

The current `PaletteImporter` base class requires `_import_palette_impl()` and
cannot represent filament import. Two designs should be evaluated:

### Capability-based general importer

A generalized importer could declare `supports_colors` and
`supports_filaments`, then provide `import_palette()` and
`import_filaments()` operations similar to the exporter base class.

This gives a symmetric public surface, but changing or renaming
`PaletteImporter` requires a compatibility plan and risks making one base class
responsible for unrelated payload types.

### Shared infrastructure with focused importer classes

An internal base could own path validation, dependency handling, and format
detection, while public `PaletteImporter` and `FilamentImporter` classes own
their respective result types and parsing hooks.

This is the preferred starting point because it preserves separation of
concerns and can retain the existing `PaletteImporter` API. The registry can
index importers by format name, extension, and supported data kind so formats
sharing `.json` can still be detected by content.

The design should not duplicate dependency, metadata, registry, or path
validation logic between the two importer types.

## Proposed Python workflows

Format conversion without persistence:

```python
imported = get_filament_importer("hueforge").import_filaments(
    "hueforge-library.json"
)

get_exporter("autoforge").export_filament_data(
    imported,
    "autoforge-library.csv",
)
```

Importing into user data:

```python
imported = get_filament_importer("hueforge").import_filaments(
    "hueforge-library.json"
)

exporter = get_exporter("user_filaments")
plan = exporter.plan_filament_data(imported)

print(plan.summary)
exporter.apply(plan)
```

Importing ownership is a separate operation after the catalog contains every
filament that should be eligible for resolution:

```python
owned_selection = get_owned_filament_importer("hueforge").import_owned(
    "hueforge-library.json"
)

exporter = get_exporter("owned_filaments")
plan = exporter.plan_owned_filaments(owned_selection)

print(plan.summary)
exporter.apply(plan)
```

The exact class and method names are illustrative, not approved API.

## Proposed CLI direction

The Python design should stay modular, while the CLI can offer a convenient
orchestrated command. Illustrative commands:

```text
# Inspect without writing (default).
color-tools filament --import hueforge --input library.json --to user-filaments

# Apply reviewed catalog additions only.
color-tools filament --import hueforge --input library.json \
    --to user-filaments --apply

# Independently inspect and then apply ownership from the same source.
color-tools filament --import-owned hueforge --input library.json
color-tools filament --import-owned hueforge --input library.json --apply

# Convert between external formats without changing user data.
color-tools filament --import hueforge --input library.json \
    --export autoforge --output library.csv
```

The final CLI grammar should be designed alongside the Python API. It must make
dry-run versus apply behavior unmistakable and print the structured plan before
writing.

## Initial format priorities

Suggested order after the framework contracts are approved:

1. `FilamentMetadata`, `FilamentExportData`, and the symmetric filament
   importer/exporter base contracts. **Implemented.**
2. Color Tools user-color importer/exporter round trips, including sidecar
   updates. **Implemented for the Python API; CLI orchestration remains a later
   decision.**
3. Color Tools user-filament importer/exporter round trips, including sidecar
   updates. **Implemented for the Python API; catalog writes do not modify
   ownership.**
4. HueForge filament catalog importer and the existing HueForge exporter.
   **Implemented for the Python API:** both known HueForge envelopes parse to
   `FilamentExportData`; a reusable reconciliation plan ranks existing records,
   requires caller choices for ambiguity, generates collision-safe IDs for new
   records, and remaps ownership to final IDs. Persistence remains an explicit
   later exporter operation.
5. Independent owned-filament import/export, followed by a HueForge ownership
   adapter that resolves against the current catalog without changing it.
   **Implemented for the Python API:** `OwnedFilamentsExporter` consumes final
   IDs directly or from reconciled `FilamentExportData`, validates them against
   the effective catalog, and plans an additive atomic update. HueForge needs no
   coupled writer: its importer and reconciler already supply the generic final
   owned-ID selection. CLI orchestration remains a later decision.
6. Research import adapters for other actively used filament-management
   systems before committing to their schemas.

Support for a third-party format should be based on verified format
documentation and representative files, not inferred from one sample.

## Testing requirements

The implementation should include:

- importer metadata, capability, registry, and dependency contract tests;
- malformed HueForge field, type, UUID, color, TD, and ownership matrices;
- `FilamentMetadata` normalization, ownership, and property-preservation tests;
- semantic round trips where the two formats carry equivalent information;
- explicit lossiness tests where fields cannot round-trip;
- deterministic ID generation and collision tests;
- core, user, ambiguous, and unmatched reconciliation fixtures;
- merge-policy tests for each destination type;
- dry-run tests proving no file or sidecar changes;
- atomic-write and interrupted-operation recovery tests;
- validation of the complete prospective file before replacement;
- sidecar regeneration and verification tests;
- idempotence tests for repeated imports; and
- CLI exit-code, summary, conflict, and apply-confirmation tests.

Round-trip tests should compare supported semantics rather than requiring
byte-for-byte reproduction of an external file. For example, HueForge does not
carry a Color Tools finish, and its UUID cannot reconstruct the original Color
Tools ID.

## Decisions required before implementation

1. Extend the implemented format-neutral reconciliation contract to additional
   external formats only after their real schemas and matching problems are
   reviewed. HueForge currently uses normalized maker/type/finish/color layouts,
   maker synonyms, optional fuzzy similarity, and hex/TD supporting evidence.
2. Deterministic ID generation and collision handling are implemented in the
   base reconciler: every plan reserves canonical IDs against the catalog and
   earlier plan entries, using `-2`, `-3`, and later suffixes.
3. The planning/result pattern is implemented for additive ownership updates
   without changing existing path-returning export APIs. Any future removal or
   full-inventory synchronization mode requires a separate explicit contract.
4. Specify external-format reconciliation policy. User-filament persistence
   now uses `error`, `skip`, and `replace` for same-ID differences; different
   IDs remain distinct records and descriptive matches produce warnings.
5. The generic owned-filament selection contract is implemented through final
   Color Tools IDs in `FilamentMetadata.owned_filament_ids`; format-specific
   ambiguity is resolved before the additive ownership exporter is called.
6. Decide whether the first release exposes Python only or also includes the
   orchestration CLI.

## Non-goals for the first revision

- Writing directly to bundled core data.
- Importing or editing `user-synonyms.json`; synonym reconciliation is a
  separate concern from color, filament, and inventory transfer.
- Treating RGB equality as filament identity.
- Adding ownership or external UUID fields to `FilamentRecord`.
- Silently guessing ambiguous matches, material types, or finishes.
- Building a universal schema-mapping language before concrete formats require
  it.
- Changing all existing exporters to return structured result objects.
- Guaranteeing lossless round trips when the source and destination formats do
  not represent the same fields.
- Adding an AutoForge importer. AutoForge consumes filament data for model
  generation but does not provide a filament-library source format to import;
  its existing exporter remains useful as an output destination.

