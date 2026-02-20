# Planning Document: Owned Filaments Management System

**Document Purpose**: Explore approaches for implementing a system to track which filaments a user owns, allowing them to filter searches and queries to their personal inventory.

**Status**: PLANNING ONLY - No implementation yet  
**Date**: February 20, 2026

---

## Problem Statement

Users need a way to:
1. Track which filaments from the database they personally own
2. Filter filament searches to show only owned filaments
3. Get color matching results from their personal inventory

**Key Constraint**: The `user-filaments.json` file is for **adding custom filaments** to the database, NOT for tracking ownership of existing filaments.

---

## Understanding Existing Architecture

### Current User Data System

From `docs/Customization.md`:

- **`user-filaments.json`** - Adds custom filaments to the database
  - Purpose: Extend the database with filaments NOT in the core list
  - Format: Full filament records with all properties
  - Use case: "My local shop has a filament not in your database"

- **`user-colors.json`** - Adds custom colors to the database
  - Same pattern as user-filaments.json

- **`user-synonyms.json`** - Adds maker name synonyms
  - Different pattern - extends/overrides synonym mappings

### Filament Record Structure

```python
@dataclass(frozen=True)
class FilamentRecord:
    id: str                              # e.g., "bambu-lab-pla-basic-black"
    maker: str
    type: str                            # PLA, PETG, ABS, etc.
    finish: Optional[str]
    color: str
    hex: str                             # Color code
    td_value: Optional[float]            # Translucency
    other_names: Optional[List[str]]
    source: str                          # Tracks which JSON file
```

### Current Filtering Capabilities

```python
FilamentPalette.filter(
    maker=...,
    type_name=...,
    finish=...,
    color=...
)

FilamentPalette.nearest_filament(target_rgb, maker=..., type_name=..., finish=...)
FilamentPalette.nearest_filaments(target_rgb, count=5, maker=..., ...)
```

---

## Approach 1: Separate Tracking File (ID-Based References)

### Concept
Create a new file `owned-filaments.json` that contains a list of filament IDs.

### File Format Options

**Option A: Simple List**
```json
[
  "bambu-lab-pla-basic-black",
  "polymaker-pla-matte-red",
  "my-custom-filament-id"
]
```

**Option B: Structured**
```json
{
  "owned_ids": [
    "bambu-lab-pla-basic-black",
    "polymaker-pla-matte-red"
  ],
  "notes": {
    "bambu-lab-pla-basic-black": "Bought 2024-01-15, 2 spools left"
  }
}
```

### Pros
✅ Lightweight - just references, not full records  
✅ Works with core and user-defined filaments  
✅ Clear separation from user-filaments.json  
✅ Fast lookup (O(1) with Set)  
✅ Easy to maintain manually  
✅ Can track custom filaments too

### Cons
❌ Requires users to know filament IDs  
❌ No rich metadata (quantity, location, purchase date)  
❌ IDs can be long and complex  
❌ Needs CLI help to find IDs

### Possible Workflows
- **Basic filtering**: `--owned` flag
- **Finding IDs**: CLI command to list/search
- **Managing**: CLI commands to add/remove
- **Exporting**: Export owned list to CSV/JSON

---

## Approach 2: Extended FilamentRecord with Metadata

### Concept
Add optional metadata to FilamentRecord and store in user-filaments.json.

### Extended Record Format
```json
{
  "id": "bambu-lab-pla-basic-black",
  "maker": "Bambu Lab",
  "type": "PLA",
  "finish": "Basic",
  "color": "Black",
  "hex": "#000000",
  "owned_metadata": {
    "quantity": 2,
    "location": "Shelf A",
    "purchase_date": "2024-01-15",
    "price": 24.99,
    "notes": "Good for structural parts"
  }
}
```

### Pros
✅ Rich metadata support  
✅ Single file for user additions  
✅ Can track quantities and locations  
✅ Natural extension of existing pattern

### Cons
❌ Conflates two different purposes (adding vs tracking)  
❌ Duplicates core filament data in user file  
❌ Larger files  
❌ More complex user file structure  
❌ Violates single responsibility principle

### Possible Workflows
- **Inventory management**: Track quantities, locations
- **Purchase tracking**: Costs, dates
- **Project planning**: Allocate filaments to projects

---

## Approach 3: SQLite Database for Inventory

### Concept
Use a lightweight SQLite database for inventory management.

### Database Schema
```sql
CREATE TABLE owned_filaments (
    filament_id TEXT PRIMARY KEY,
    quantity INTEGER DEFAULT 1,
    location TEXT,
    purchase_date DATE,
    price REAL,
    notes TEXT
);
```

### Pros
✅ Proper database with query capabilities  
✅ Rich metadata and relationships  
✅ Can track history (purchases, usage)  
✅ Supports complex queries  
✅ Scales well to large inventories

### Cons
❌ Adds dependency (though SQLite is built-in)  
❌ More complex for users to edit manually  
❌ Breaks the "plain text files" philosophy  
❌ Harder to version control  
❌ Overkill for simple use cases

### Possible Workflows
- **Advanced inventory**: Full CRUD operations
- **Reporting**: Generate usage reports
- **Multi-user**: Share database across team

---

## Approach 4: Multi-Level Tagging System

### Concept
Allow users to tag filaments with multiple categories beyond just "owned".

### File Format
```json
{
  "tags": {
    "owned": [
      "bambu-lab-pla-basic-black",
      "polymaker-pla-matte-red"
    ],
    "favorites": [
      "bambu-lab-pla-silk-plus-red"
    ],
    "low-stock": [
      "polymaker-pla-matte-red"
    ],
    "discontinued": [
      "old-maker-pla-blue"
    ]
  }
}
```

### Pros
✅ Flexible - supports multiple workflows  
✅ User can create custom tags  
✅ Future-proof  
✅ One file for all categorizations

### Cons
❌ More complex mental model  
❌ Might be over-engineered for initial need  
❌ Needs UI/CLI for tag management

### Possible Workflows
- **Multi-category**: owned, favorites, wishlist, low-stock
- **Projects**: Tag by project name
- **Custom organization**: User-defined tags
- **Filtering**: `--tag owned --tag favorites`

---

## Approach 5: Inventory Configuration with Multiple Lists

### Concept
Structured config file with multiple named inventories.

### File Format
```json
{
  "inventories": {
    "owned": {
      "description": "Filaments I currently own",
      "filaments": ["bambu-lab-pla-basic-black", ...]
    },
    "wishlist": {
      "description": "Filaments to buy",
      "filaments": ["prusament-pla-galaxy-black", ...]
    },
    "workshop_a": {
      "description": "Filaments at Workshop A location",
      "filaments": ["bambu-lab-pla-basic-black", ...]
    }
  },
  "default_inventory": "owned"
}
```

### Pros
✅ Supports complex workflows (multiple locations)  
✅ Flexible for different use cases  
✅ Named inventories are self-documenting

### Cons
❌ More complex than single list  
❌ Might be confusing for simple cases  
❌ Requires inventory management commands

### Possible Workflows
- **Multiple locations**: Per-location inventories
- **Wishlists**: Separate from owned
- **Projects**: Project-specific inventories
- **Filtering**: `--inventory workshop_a`

---

## Comparison Matrix

| Feature | Approach 1 | Approach 2 | Approach 3 | Approach 4 | Approach 5 |
|---------|------------|------------|------------|------------|------------|
| **Simplicity** | ⭐⭐⭐⭐⭐ | ⭐⭐⭐ | ⭐⭐ | ⭐⭐⭐⭐ | ⭐⭐⭐ |
| **Manual Editing** | ⭐⭐⭐⭐⭐ | ⭐⭐⭐ | ⭐ | ⭐⭐⭐⭐ | ⭐⭐⭐⭐ |
| **Metadata Support** | ⭐ | ⭐⭐⭐⭐⭐ | ⭐⭐⭐⭐⭐ | ⭐⭐ | ⭐⭐ |
| **Performance** | ⭐⭐⭐⭐⭐ | ⭐⭐⭐ | ⭐⭐⭐⭐ | ⭐⭐⭐⭐ | ⭐⭐⭐⭐ |
| **Flexibility** | ⭐⭐ | ⭐⭐⭐ | ⭐⭐⭐⭐⭐ | ⭐⭐⭐⭐⭐ | ⭐⭐⭐⭐ |
| **Separation of Concerns** | ⭐⭐⭐⭐⭐ | ⭐⭐ | ⭐⭐⭐⭐⭐ | ⭐⭐⭐⭐⭐ | ⭐⭐⭐⭐⭐ |

---

## Alternative Workflows to Consider

Beyond simple owned/not-owned filtering, users might want:

1. **Location-based filtering**: "Show me filaments in Workshop A"
2. **Project-based filtering**: "Show me filaments for Project X"
3. **Quantity tracking**: "Show me low-stock filaments"
4. **Purchase planning**: "Compare owned vs needed"
5. **Cost tracking**: "What's my inventory value?"
6. **Multi-user/location**: "Show all available filaments across locations"
7. **Wishlist management**: "Track filaments I want to buy"
8. **Historical tracking**: "When did I buy this? How much have I used?"

---

## Questions for Decision

1. **File Format**: Simple list vs structured object vs database?
2. **CLI Interface**: Single flag (`--owned`) vs multiple commands vs filtering DSL?
3. **Metadata**: Plan for it now or add later?
4. **Helper Commands**: Include in initial implementation?
5. **Workflow Priority**: Which workflows matter most to users?
6. **Backwards Compatibility**: How to handle future format changes?
7. **Multi-file vs Single-file**: Separate files for different lists?

---

## Recommended Approach (If I Had to Choose)

**Approach 1** (ID-based references) for MVP, with path to expand:
- Simplest to start
- Clear separation of concerns
- Can evolve format later
- Good for 80% of use cases

**But** consider user feedback on which workflows matter most before deciding!

---

## Next Steps

1. **Review this document** - discuss approaches and tradeoffs
2. **Answer decision questions** - clarify requirements
3. **Prioritize workflows** - which ones matter most?
4. **Choose approach** - based on user needs
5. **Define exact specifications** - file format, API, CLI
6. **Get approval** before implementing
7. **Implement incrementally** with feedback

---

**End of Planning Document**

*This is a planning document only. No code has been implemented.*
