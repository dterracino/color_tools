"""
Interactive filament library manager using prompt_toolkit TUI.

This module provides a rich terminal user interface for managing owned filaments,
with features like filtering, multi-select, autocomplete, and live search.

Requires the [interactive] extra:
    pip install color-match-tools[interactive]

Example:
    >>> from color_tools.interactive_manager import run_interactive_manager
    >>> run_interactive_manager()  # Launches TUI
"""

from __future__ import annotations

import sys
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from pathlib import Path

# Check if prompt_toolkit is available
try:
    from prompt_toolkit import Application
    from prompt_toolkit.key_binding import KeyBindings
    from prompt_toolkit.layout import Layout, HSplit, VSplit, Window
    from prompt_toolkit.layout.controls import FormattedTextControl
    from prompt_toolkit.widgets import TextArea, Frame, Label
    from prompt_toolkit.styles import Style
    PROMPT_TOOLKIT_AVAILABLE = True
except ImportError:
    PROMPT_TOOLKIT_AVAILABLE = False

__all__ = [
    'run_interactive_manager',
    'check_prompt_toolkit',
    'show_install_message',
]


def check_prompt_toolkit() -> bool:
    """
    Check if prompt_toolkit is installed.
    
    Returns:
        True if prompt_toolkit is available, False otherwise
    """
    return PROMPT_TOOLKIT_AVAILABLE


def show_install_message() -> None:
    """Show helpful message if prompt_toolkit is not installed."""
    print("\n❌ Interactive mode requires prompt_toolkit")
    print("\nInstall with:")
    print("  pip install color-match-tools[interactive]")
    print("\nOr install prompt_toolkit directly:")
    print("  pip install prompt_toolkit>=3.0.0")
    print()


def run_interactive_manager(json_dir: Path | str | None = None) -> None:
    """
    Launch the interactive filament library manager TUI.
    
    Args:
        json_dir: Optional directory containing JSON data files
        
    Raises:
        SystemExit: If prompt_toolkit is not installed
    """
    if not PROMPT_TOOLKIT_AVAILABLE:
        show_install_message()
        sys.exit(1)
    
    # Import FilamentPalette here to avoid circular imports
    from .filament_palette import FilamentPalette, load_filaments, load_maker_synonyms, load_owned_filaments
    
    # Load filament palette
    if json_dir:
        from pathlib import Path
        dir_path = Path(json_dir)
        filaments = load_filaments(dir_path / 'filaments.json')
        synonyms = load_maker_synonyms(dir_path / 'maker_synonyms.json')
        owned = load_owned_filaments(dir_path / 'user' / 'owned-filaments.json')
        palette = FilamentPalette(filaments, synonyms, owned)
    else:
        palette = FilamentPalette.load_default()
    
    # Create and run the interactive manager
    manager = InteractiveFilamentManager(palette)
    manager.run()


class InteractiveFilamentManager:
    """
    Interactive TUI for managing owned filaments.
    
    Features:
    - Filter by maker, type, finish, color
    - Multi-select with spacebar
    - Live search
    - Autocomplete on fields
    - Shows owned count in real-time
    - Auto-saves changes
    """
    
    def __init__(self, palette):
        """
        Initialize the interactive manager.
        
        Args:
            palette: FilamentPalette instance with loaded filaments
        """
        if not PROMPT_TOOLKIT_AVAILABLE:
            raise ImportError("prompt_toolkit is required for interactive mode")
        
        self.palette = palette
        self.owned_ids = palette.owned_filaments.copy() if palette.owned_filaments else set()
        self.original_owned_ids = self.owned_ids.copy()  # Track original state for exit summary
        self.filtered_filaments = list(palette.records)
        
        # Filter state
        self.filter_maker = ""
        self.filter_type = ""
        self.filter_finish = ""
        self.filter_color = ""
        self.filter_mode = False
        self.filter_field_index = 0  # 0=maker, 1=type, 2=finish, 3=color
        
        # Confirmation state
        self.quit_confirm_mode = False
        
        # UI state
        self.current_index = 0
        self.scroll_offset = 0
        self.page_size = 12  # Reduced to make room for filter UI
        self.changes_made = False
        
        # Build UI
        self._build_ui()
    
    def _build_ui(self):
        """Build the prompt_toolkit UI layout."""
        # Create key bindings
        kb = KeyBindings()
        
        @kb.add('q')
        def quit_app(event):
            """Quit the application."""
            if self.changes_made:
                # Enter quit confirmation mode
                self.quit_confirm_mode = True
                self._update_display()
            else:
                event.app.exit()
        
        @kb.add('y')
        def confirm_yes(event):
            """Confirm save and quit."""
            if self.quit_confirm_mode:
                self.palette.owned_filaments = self.owned_ids
                self.palette.save_owned()
                event.app.exit()
        
        @kb.add('n')
        def confirm_no(event):
            """Quit without saving."""
            if self.quit_confirm_mode:
                event.app.exit()
        
        @kb.add('escape')
        def escape_action(event):
            """Exit filter/confirm mode or quit application."""
            if self.filter_mode:
                self.filter_mode = False
                self._update_display()
            elif self.quit_confirm_mode:
                self.quit_confirm_mode = False
                self._update_display()
            else:
                # Escape without unsaved changes = quit
                if not self.changes_made:
                    event.app.exit()
        
        @kb.add('space')
        def toggle_owned(event):
            """Toggle owned status of current filament."""
            if not self.filter_mode and not self.quit_confirm_mode and self.filtered_filaments:
                filament = self.filtered_filaments[self.current_index]
                if filament.id in self.owned_ids:
                    self.owned_ids.remove(filament.id)
                else:
                    self.owned_ids.add(filament.id)
                self.changes_made = True
                self._update_display()
        
        @kb.add('down')
        def move_down(event):
            """Move selection down."""
            if not self.filter_mode and not self.quit_confirm_mode and self.current_index < len(self.filtered_filaments) - 1:
                self.current_index += 1
                if self.current_index >= self.scroll_offset + self.page_size:
                    self.scroll_offset += 1
                self._update_display()
        
        @kb.add('up')
        def move_up(event):
            """Move selection up."""
            if not self.filter_mode and not self.quit_confirm_mode and self.current_index > 0:
                self.current_index -= 1
                if self.current_index < self.scroll_offset:
                    self.scroll_offset -= 1
                self._update_display()
        
        @kb.add('home')
        def jump_to_start(event):
            """Jump to first filament."""
            if not self.filter_mode and not self.quit_confirm_mode and self.filtered_filaments:
                self.current_index = 0
                self.scroll_offset = 0
                self._update_display()
        
        @kb.add('end')
        def jump_to_end(event):
            """Jump to last filament."""
            if not self.filter_mode and not self.quit_confirm_mode and self.filtered_filaments:
                max_index = len(self.filtered_filaments) - 1
                self.current_index = max_index
                # Position scroll so last item is visible
                self.scroll_offset = max(0, max_index - self.page_size + 1)
                self._update_display()
        
        @kb.add('pagedown')
        def page_down(event):
            """Move selection down by one page."""
            if not self.filter_mode and not self.quit_confirm_mode and self.filtered_filaments:
                max_index = len(self.filtered_filaments) - 1
                self.current_index = min(self.current_index + self.page_size, max_index)
                # Adjust scroll to keep selection visible
                if self.current_index >= self.scroll_offset + self.page_size:
                    self.scroll_offset = min(self.current_index - self.page_size + 1, max_index - self.page_size + 1)
                self._update_display()
        
        @kb.add('pageup')
        def page_up(event):
            """Move selection up by one page."""
            if not self.filter_mode and not self.quit_confirm_mode and self.filtered_filaments:
                self.current_index = max(self.current_index - self.page_size, 0)
                # Adjust scroll to keep selection visible
                if self.current_index < self.scroll_offset:
                    self.scroll_offset = max(self.current_index, 0)
                self._update_display()
        
        @kb.add('s')
        def save_and_continue(event):
            """Save changes."""
            if not self.filter_mode and not self.quit_confirm_mode:
                self.palette.owned_filaments = self.owned_ids
                self.palette.save_owned()
                self.changes_made = False
                self._update_display()
        
        @kb.add('r')
        def revert_changes(event):
            """Revert unsaved ownership changes."""
            if not self.filter_mode and not self.quit_confirm_mode:
                # Reload from saved state
                self.owned_ids = self.palette.owned_filaments.copy() if self.palette.owned_filaments else set()
                self.changes_made = False
                self._update_display()
        
        @kb.add('c')
        def clear_filters(event):
            """Clear all filters."""
            if not self.filter_mode and not self.quit_confirm_mode:
                self.filter_maker = ""
                self.filter_type = ""
                self.filter_finish = ""
                self.filter_color = ""
                self._apply_filters()
                self._update_display()
        
        @kb.add('f')
        def enter_filter_mode(event):
            """Enter filter mode."""
            if not self.filter_mode and not self.quit_confirm_mode:
                self.filter_mode = True
                self.filter_field_index = 0
                self._update_display()
        
        @kb.add('tab')
        def next_filter_field(event):
            """Move to next filter field."""
            if self.filter_mode:
                self.filter_field_index = (self.filter_field_index + 1) % 4
                self._update_display()
        
        @kb.add('s-tab')  # Shift+Tab
        def prev_filter_field(event):
            """Move to previous filter field."""
            if self.filter_mode:
                self.filter_field_index = (self.filter_field_index - 1) % 4
                self._update_display()
        
        @kb.add('backspace')
        def backspace_filter(event):
            """Backspace in filter mode."""
            if self.filter_mode:
                if self.filter_field_index == 0 and self.filter_maker:
                    self.filter_maker = self.filter_maker[:-1]
                elif self.filter_field_index == 1 and self.filter_type:
                    self.filter_type = self.filter_type[:-1]
                elif self.filter_field_index == 2 and self.filter_finish:
                    self.filter_finish = self.filter_finish[:-1]
                elif self.filter_field_index == 3 and self.filter_color:
                    self.filter_color = self.filter_color[:-1]
                self._apply_filters()
                self._update_display()
        
        # Handle text input in filter mode (only catch specific keys that aren't bound)
        from prompt_toolkit.filters import Condition
        
        @kb.add('<any>', filter=Condition(lambda: self.filter_mode))
        def handle_text_input(event):
            """Handle text input in filter mode."""
            if event.data and len(event.data) == 1 and event.data.isprintable():
                if self.filter_field_index == 0:
                    self.filter_maker += event.data
                elif self.filter_field_index == 1:
                    self.filter_type += event.data
                elif self.filter_field_index == 2:
                    self.filter_finish += event.data
                elif self.filter_field_index == 3:
                    self.filter_color += event.data
                self._apply_filters()
                self._update_display()
        
        self.kb = kb
        
        # Create the main display control
        self.main_control = FormattedTextControl(
            text=self._get_display_text,
            focusable=True,
            key_bindings=kb
        )
        
        # Create layout
        # Height: header(3) + filters(3 when active) + filaments(12) + footer(3) = 18-21
        self.root_container = HSplit([
            Window(content=self.main_control)
        ])
        
        self.layout = Layout(self.root_container)
        
        # Define styling
        style = Style.from_dict({
            'border': 'bold',
            'owned': 'cyan',
            'selected': 'reverse',
            'selected.owned': 'reverse cyan',
            'filter': 'green',
            'filter.label': 'yellow',
            'filter.active': 'yellow bold reverse',
            'unsaved': 'yellow bold',
        })
        
        # Create application
        self.app = Application(
            layout=self.layout,
            key_bindings=kb,
            style=style,
            full_screen=False,
            mouse_support=True
        )
    
    def _get_display_text(self):
        """Generate the formatted text for display."""
        result = []
        
        # Header
        total = len(self.palette.records)
        owned_count = len(self.owned_ids)
        filtered_count = len(self.filtered_filaments)
        
        result.append(('class:border', '╭─── Filament Library Manager ───────────────────────────────────────────────────╮\n'))
        result.append(('', f'│ {total} total | '))
        result.append(('class:owned', f'{owned_count} owned'))
        if self.changes_made:
            result.append(('class:unsaved', '*'))  # Yellow asterisk for unsaved changes
        result.append(('', f' | Showing {filtered_count} filaments'))
        # Pad to frame width (80 chars inside, +2 for borders)
        info_line = f'{total} total | {owned_count} owned | Showing {filtered_count} filaments'
        if self.changes_made:
            info_line += '*'
        padding = 78 - len(info_line)
        if padding > 0:
            result.append(('', ' ' * padding))
        result.append(('', ' │\n'))
        result.append(('class:border', '├────────────────────────────────────────────────────────────────────────────────┤\n'))
        
        # Filter UI
        if self.filter_mode:
            # Show filter input fields
            result.append(('', '│ '))
            result.append(('class:filter.label', 'FILTER MODE'))
            filter_header = 'FILTER MODE (Tab=next field, Esc=exit)'
            padding = 78 - len(filter_header)
            result.append(('', f' (Tab=next field, Esc=exit){" " * padding} │\n'))
            result.append(('class:border', '├────────────────────────────────────────────────────────────────────────────────┤\n'))
            
            # Filter fields
            fields = [
                ('Maker ', self.filter_maker, 0),
                ('Type  ', self.filter_type, 1),
                ('Finish', self.filter_finish, 2),
                ('Color ', self.filter_color, 3),
            ]
            
            for label, value, idx in fields:
                result.append(('', '│ '))
                if idx == self.filter_field_index:
                    result.append(('class:filter.active', f'{label}: '))
                    result.append(('class:filter.active', f'{value}_'))  # Cursor
                    field_content = f'{label}: {value}_'
                else:
                    result.append(('class:filter.label', f'{label}: '))
                    result.append(('', value))
                    field_content = f'{label}: {value}'
                # Pad to frame width
                padding = 78 - len(field_content)
                if padding > 0:
                    result.append(('', ' ' * padding))
                result.append(('', ' │\n'))
            
            result.append(('class:border', '├────────────────────────────────────────────────────────────────────────────────┤\n'))
        elif any([self.filter_maker, self.filter_type, self.filter_finish, self.filter_color]):
            # Show active filters (compact view when not in filter mode)
            filter_parts = ['Filters: ']
            if self.filter_maker:
                filter_parts.append(f'Maker={self.filter_maker} ')
            if self.filter_type:
                filter_parts.append(f'Type={self.filter_type} ')
            if self.filter_finish:
                filter_parts.append(f'Finish={self.filter_finish} ')
            if self.filter_color:
                filter_parts.append(f'Color={self.filter_color} ')
            filter_line = ''.join(filter_parts).rstrip()
            
            result.append(('', '│ '))
            result.append(('class:filter', filter_line))
            # Pad to frame width
            padding = 78 - len(filter_line)
            if padding > 0:
                result.append(('', ' ' * padding))
            result.append(('', ' │\n'))
            result.append(('class:border', '├────────────────────────────────────────────────────────────────────────────────┤\n'))
        
        # Filament list
        visible_start = self.scroll_offset
        visible_end = min(self.scroll_offset + self.page_size, len(self.filtered_filaments))
        
        for i in range(visible_start, visible_end):
            filament = self.filtered_filaments[i]
            is_owned = filament.id in self.owned_ids
            is_selected = i == self.current_index
            
            # Build the line
            checkbox = '[✓]' if is_owned else '[ ]'
            marker = '>' if is_selected else ' '
            
            # Format: "  > [✓] Maker - Type Finish - Color"
            line_text = f"{marker} {checkbox} {filament.maker} - {filament.type}"
            if filament.finish:
                line_text += f" {filament.finish}"
            line_text += f" - {filament.color}"
            
            # Truncate if too long (leave room for padding)
            max_len = 78
            if len(line_text) > max_len:
                line_text = line_text[:max_len - 3] + "..."
            
            # Apply styling
            result.append(('', '│ '))
            if is_selected:
                if is_owned:
                    result.append(('class:selected.owned', line_text))
                else:
                    result.append(('class:selected', line_text))
            else:
                if is_owned:
                    result.append(('class:owned', line_text))
                else:
                    result.append(('', line_text))
            
            # Pad to frame width
            padding = max_len - len(line_text)
            if padding > 0:
                result.append(('', ' ' * padding))
            result.append(('', ' │\n'))
        
        # Fill remaining space
        for _ in range(visible_end, visible_start + self.page_size):
            result.append(('', '│ '))
            result.append(('', ' ' * 78))  # Padding
            result.append(('', ' │\n'))
        
        # Footer
        result.append(('class:border', '├────────────────────────────────────────────────────────────────────────────────┤\n'))
        
        result.append(('', '│ '))
        if self.quit_confirm_mode:
            footer_text = 'Save changes? y=yes | n=no | Esc=cancel'
        elif self.filter_mode:
            footer_text = 'Type to filter | Tab=next | Backspace=delete | Esc=exit filter'
        else:
            footer_text = 'Spc=toggle | ↑↓Pg/Home/End | (f)ilter | (c)lear | (r)evert | (s)ave | (q)uit'
        
        result.append(('', footer_text))
        
        # Pad to frame width
        padding = 78 - len(footer_text)
        if padding > 0:
            result.append(('', ' ' * padding))
        result.append(('', ' │\n'))
        result.append(('class:border', '╰────────────────────────────────────────────────────────────────────────────────╯'))
        
        return result
    
    def _show_exit_summary(self):
        """Display summary of changes made during session."""
        # Compare original state to final saved state
        final_saved = self.palette.owned_filaments if self.palette.owned_filaments else set()
        
        added = final_saved - self.original_owned_ids
        removed = self.original_owned_ids - final_saved
        
        if added or removed:
            print("\n📊 Session Summary:")
            print("─" * 60)
            
            if added:
                print(f"✅ Added {len(added)} filament(s) to owned list:")
                for filament_id in sorted(added):
                    # Find the filament record
                    filament = next((f for f in self.palette.records if f.id == filament_id), None)
                    if filament:
                        print(f"   + {filament.maker} - {filament.type} {filament.finish or ''} - {filament.color}")
                    else:
                        print(f"   + {filament_id}")
                print()
            
            if removed:
                print(f"❌ Removed {len(removed)} filament(s) from owned list:")
                for filament_id in sorted(removed):
                    # Try to find in records (might not exist if was invalid ID)
                    filament = next((f for f in self.palette.records if f.id == filament_id), None)
                    if filament:
                        print(f"   - {filament.maker} - {filament.type} {filament.finish or ''} - {filament.color}")
                    else:
                        print(f"   - {filament_id}")
                print()
            
            print(f"Total owned: {len(self.original_owned_ids)} → {len(final_saved)}")
            print("─" * 60)
        else:
            print("\n✨ No changes made to owned filaments.")
        
        print()  # Extra newline for spacing
    
    def _update_display(self):
        """Force display refresh."""
        if hasattr(self, 'app'):
            self.app.invalidate()
    
    def _apply_filters(self):
        """Apply current filters to filament list."""
        filtered = self.palette.records
        
        # Apply filters
        if self.filter_maker:
            filtered = [f for f in filtered if self.filter_maker.lower() in f.maker.lower()]
        if self.filter_type:
            filtered = [f for f in filtered if self.filter_type.lower() in f.type.lower()]
        if self.filter_finish:
            filtered = [f for f in filtered if f.finish and self.filter_finish.lower() in f.finish.lower()]
        if self.filter_color:
            filtered = [f for f in filtered if self.filter_color.lower() in f.color.lower()]
        
        self.filtered_filaments = filtered
        self.current_index = 0
        self.scroll_offset = 0
    
    def run(self):
        """Run the interactive manager application."""
        try:
            self.app.run()
        except KeyboardInterrupt:
            # Save on Ctrl+C
            if self.changes_made:
                self.palette.owned_filaments = self.owned_ids
                self.palette.save_owned()
                print("\n✓ Changes saved")
        finally:
            # Show summary after app exits (when terminal is back to normal)
            self._show_exit_summary()
