# Post-7.0 import/export update

## Status

Post-7.0 work in progress. The initial format-neutral transfer and base-contract
phase is implemented:

- `FilamentMetadata` and `FilamentExportData` carry collection metadata,
  ownership IDs, format properties, and ordered filament records.
- `FilamentImporter` shares path, dependency, availability, and detection
  behavior with `PaletteImporter` without requiring palette parsing hooks.
- Exporters accept `FilamentExportData` through `export_filament_data()` and
  fall back to existing filament export when they do not consume metadata.

Concrete filament importers, filament-aware registry dispatch, reconciliation,
and user-data writers remain pending. Compatibility and safety decisions below
must be resolved before those stateful operations are implemented.

## Motivation

The current import and export systems are not symmetric:

- Exporters can export raw `ColorRecord` lists, `FilamentRecord` lists, and
  metadata-bearing `PaletteExportData` values.
- Importers only import color palettes. `PaletteImporter.import_palette()`
  returns `PaletteExportData`.
- There is no filament-import contract, no `FilamentExportData` equivalent,
  and no HueForge filament importer.
- Neither framework provides a supported path for merging imported records
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
- reporting planned additions, updates, skips, and ownership changes;
- validating the complete prospective document;
- writing atomically; and
- regenerating any integrity sidecar defined for the destination.

`user-colors.json` and `user-filaments.json` currently have sidecars.
`owned-filaments.json` does not, because it is mutable inventory state. This
plan should not add an ownership sidecar unless the broader integrity policy is
changed together with every existing ownership-writing path.

The user-data destinations should be registered exporters:

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
concept.

The workflow remains modular:

```python
imported = hueforge_importer.import_filaments("library.json")
exporter = get_exporter("user_filaments")
plan = exporter.plan_filament_data(imported)
exporter.apply(plan)
```

A CLI command may orchestrate those steps for convenience without making the
format importer depend on the user-data exporter.

## Filament transfer model requirements

A plain `list[FilamentRecord]` is sufficient for format-to-format conversion,
but it cannot fully represent a HueForge import. A HueForge entry also has:

- an `Owned` flag;
- an external UUID;
- no Color Tools `finish` field; and
- no guaranteed Color Tools filament ID.

The import result therefore needs to retain import-only information until
catalog reconciliation is complete. Two reasonable shapes are:

1. A filament collection plus separate ownership and external-identity maps.
2. A list of import entries, each containing a `FilamentRecord` candidate,
   optional ownership, and optional external identifier.

The second shape avoids relying on list indexes and keeps format-specific
identity associated with the record it describes. `FilamentExportData` can
expose its ordered `.filaments` list to ordinary exporters while user-data and
ownership exporters use the complete entries.

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

Recommended reconciliation order:

1. Match an imported entry to a known core or user record using verified,
   normalized identity fields.
2. If exactly one existing record matches, reuse its Color Tools ID and do not
   create a duplicate user filament.
3. If no record matches, propose a deterministic new Color Tools ID and report
   it before writing.
4. If multiple records match, report ambiguity and require caller input rather
   than guessing.
5. Add an ID to `owned-filaments.json` only after it resolves to an existing or
   newly persisted Color Tools filament.

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

Ownership export is a reconciliation operation over `FilamentExportData`, not
an intrinsic filament-record field. The ownership-aware exporter should accept
resolved Color Tools IDs and merge them with the existing `owned_filaments`
list.

The current runtime contract is also ID-based. A user override retains the
system filament's ID, so an existing ownership reference follows the effective
replacement record automatically. A new record in `user-filaments.json` can be
owned by adding its new ID. `--validate-user-files` validates the ownership
schema and resolves every owned ID against the fully merged system-plus-user
catalog.

For additive imports, an external `Owned: false` value means only that the
record is not added to local ownership; it must not remove an existing local
ownership reference. Removing ownership requires an explicit inventory
synchronization or replacement operation.

For external inventory systems, results should be divided into:

- matched and already owned;
- matched and newly marked owned;
- newly created user filaments that can now be marked owned;
- unmatched entries; and
- ambiguous entries requiring review.

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

Because a HueForge import may update both `user-filaments.json` and
`owned-filaments.json`, the plan must validate both prospective documents
before either is replaced. The implementation should also define recovery if
the process is interrupted between the two atomic replacements.

## Result and reporting objects

Normal format exporters can continue returning the destination path. Stateful
user-data operations need a structured result that can support both Python and
CLI callers. A result should report:

- source and destination paths;
- dry-run or applied status;
- parsed, accepted, added, updated, skipped, and rejected counts;
- ownership additions and already-owned counts;
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
plan = exporter.plan_filament_data(
    imported,
    import_owned=True,
)

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

# Apply reviewed catalog additions and ownership changes.
color-tools filament --import hueforge --input library.json \
    --to user-filaments --import-owned --apply

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
   importer/exporter base contracts.
2. Color Tools user-color and user-filament exporters, including sidecar
   updates.
3. HueForge filament importer with ownership capture and reconciliation.
4. Owned-filament export and the combined HueForge catalog/inventory workflow.
5. Color Tools' own JSON import/export round trips.
6. AutoForge filament import if its documented format contains enough identity
   information.
7. Research import adapters for other actively used filament-management
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
- atomic-write and interrupted-multi-file recovery tests;
- validation of the complete prospective file before replacement;
- sidecar regeneration and verification tests;
- idempotence tests for repeated imports; and
- CLI exit-code, summary, conflict, and apply-confirmation tests.

Round-trip tests should compare supported semantics rather than requiring
byte-for-byte reproduction of an external file. For example, HueForge does not
carry a Color Tools finish, and its UUID cannot reconstruct the original Color
Tools ID.

## Decisions required before implementation

1. Define canonical color and filament identity keys for reconciliation.
2. Define deterministic ID generation and collision handling for new user
   filaments.
3. Define the planning and structured-result additions for state-aware
   exporters while preserving existing path-returning export APIs.
4. Specify merge policies and whether updates may replace only user records or
   may also shadow core records.
5. Define safe coordination of `user-filaments.json`,
   `owned-filaments.json`, and any applicable sidecars.
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

