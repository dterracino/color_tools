# CLI Size and Architecture Notes

## Current State

The CLI module (`cli.py`) has grown significantly:
- **Current size**: 1,130+ lines (more than doubled from original 453 lines)
- **Single monolithic `main()` function** handling all commands
- **Mixed concerns**: Argument parsing + validation + business logic + output formatting all in one place

## Core Architectural Problems

1. **Hard to test** individual command handlers
2. **Difficult to add new commands** without touching existing code
3. **Repetitive logic** scattered throughout (validation, formatting, error handling)
4. **High cyclomatic complexity** in the main function
5. **Poor separation of concerns** - everything mixed together

## Proposed Two-Phase Refactoring Plan

### Phase 1: Extract Helper Methods (Quick Wins) 🔧

**Goal**: Immediate code reduction and better organization

**Extract into shared utilities**:

**1. Validation helpers** → Move to `validation.py`:
- `_parse_hex()` → `parse_hex_color()`
- `_is_valid_lab()` → `validate_lab_range()`  
- `_is_valid_lch()` → `validate_lch_range()`

**2. Input parsing patterns** → Create `cli_utils.py`:
- `parse_color_input(args)` - handles --hex vs --value logic (repeated 4+ times)
- `get_distance_metric()` - handles metric selection + CMC params
- `load_palette_with_fallback()` - palette loading logic

**3. Output formatting** → Extract to existing modules:
- Color display logic → palette.py (add `format_color_record()`)
- Filament display logic → palette.py (add `format_filament_record()`)
- `format_json_output()`, `format_text_output()`

**4. Error handling patterns**:
- `handle_validation_error()`, `format_error_message()`

**Benefits**: 
- Immediate code reduction in main()
- Better testability of individual functions
- DRY principle - reduce repetitive code
- Can be done incrementally

### Phase 2: Handler Pattern Architecture (Long-term) 🏗️

**Goal**: Clean separation of concerns with proper architecture

**Proposed structure**:
```
color_tools/
├── cli/
│   ├── __init__.py          # Main entry point
│   ├── handlers/
│   │   ├── __init__.py      # BaseHandler class
│   │   ├── color.py         # ColorHandler
│   │   ├── filament.py      # FilamentHandler  
│   │   ├── convert.py       # ConvertHandler
│   │   ├── name.py          # NameHandler
│   │   ├── cvd.py           # CvdHandler
│   │   └── image.py         # ImageHandler
│   ├── validation.py        # Shared validation utilities
│   ├── formatting.py        # Output formatters
│   └── utils.py             # Common operations
```

**BaseHandler** provides shared functionality:
- Argument validation framework
- Common output formatting
- Error handling patterns
- Configuration management

**Command-specific handlers** focus on business logic:
- Clean, testable command implementations
- Easy to add new commands
- Clear separation of concerns

## Implementation Strategy

1. **Both phases are complementary** - not mutually exclusive
2. **Start with Phase 1** for immediate improvement
3. **Gradually migrate to Phase 2** using extracted helpers
4. **Maintain backward compatibility** throughout transition
5. **Can be done incrementally** - one command at a time

### Why This Staged Approach Works Better

**Risk Management:**
- Phase 1: Low risk extraction, easy to verify
- Phase 2: Bigger changes on a cleaner foundation

**Learning During Phase 1:**
- Discover natural boundaries between functions
- Identify common patterns that emerge
- Find the right abstraction level

**Immediate Value:**
- Code gets better **now** 
- Easier debugging and maintenance
- Functions become testable in isolation

### Concrete Example: Color Input Parsing

**Current (repeated 4+ times):**
```python
if args.hex is not None:
    try:
        rgb_val = _parse_hex(args.hex)
        val = (float(rgb_val[0]), float(rgb_val[1]), float(rgb_val[2]))
        space = "rgb"
    except ValueError as e:
        print(f"Error: {e}", file=sys.stderr)
        sys.exit(2)
else:
    val = (float(args.value[0]), float(args.value[1]), float(args.value[2]))
    space = args.space
```

**Phase 1 - Extract Helper:**
```python
# cli_utils.py
def parse_color_input(args) -> tuple[tuple[float, float, float], str]:
    """Parse color input from CLI args, handling --hex vs --value."""
    if args.hex is not None:
        rgb_val = parse_hex_color(args.hex)  # moved to validation.py
        return (float(rgb_val[0]), float(rgb_val[1]), float(rgb_val[2])), "rgb"
    else:
        return (float(args.value[0]), float(args.value[1]), float(args.value[2])), args.space

# cli.py
val, space = parse_color_input(args)
```

**Phase 2 - Handler Pattern:**
```python
# handlers/color.py  
def handle_color_command(args):
    val, space = parse_color_input(args)
    # ... rest of color logic
```

## Current Status

**Planning phase** - architectural decisions documented, ready for implementation when resources allow.

## Example Handler Code

### Basic Command Handler Pattern

**From CODE_REVIEW.md - Simple extraction approach:**

```python
def handle_color_command(args, palette):
    """Handle the color subcommand."""
    # Color command logic here
    
def handle_filament_command(args, json_path):
    """Handle the filament subcommand."""
    # Filament command logic here
    
def main():
    args = parser.parse_args()
    
    if args.command == "color":
        handle_color_command(args, palette)
    elif args.command == "filament":
        handle_filament_command(args, json_path)
    # ...
```

### Advanced Handler Architecture (Phase 2)

**Proposed BaseHandler pattern:**

```python
from abc import ABC, abstractmethod

class BaseHandler(ABC):
    """Base class for command handlers."""
    
    def __init__(self, config: Config):
        self.config = config
    
    @abstractmethod
    def execute(self, args) -> None:
        """Execute the command with given arguments."""
        pass
    
    def validate_args(self, args) -> None:
        """Validate command arguments."""
        pass
    
    def format_output(self, result, format_type: str):
        """Format output as JSON or text."""
        if format_type == "json":
            return json.dumps(result, indent=2)
        return str(result)

class ColorHandler(BaseHandler):
    """Handler for color command."""
    
    def execute(self, args) -> None:
        self.validate_args(args)
        palette = Palette.load_default()
        # Color-specific logic here
        
class FilamentHandler(BaseHandler):
    """Handler for filament command."""
    
    def execute(self, args) -> None:
        self.validate_args(args)
        palette = FilamentPalette.load_default()
        # Filament-specific logic here

# Handler registry
HANDLERS = {
    "color": ColorHandler,
    "filament": FilamentHandler,
    "convert": ConvertHandler,
    "name": NameHandler,
    "cvd": CvdHandler,
    "image": ImageHandler
}

def main():
    args = parser.parse_args()
    handler_class = HANDLERS.get(args.command)
    if handler_class:
        handler = handler_class(config)
        handler.execute(args)
```

## Notes

- This addresses the size/architecture issues, separate from the parameter context problems documented in TODO.md
- Focus is on code organization and maintainability, not user-facing functionality changes
- Both phases can proceed in parallel with other development work
- Handler examples show progression from simple extraction to full OOP architecture