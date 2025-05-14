"""
Enhanced terminal formatter for Angela CLI with improved layout and consistent styling.

This module provides responsive terminal output formatting with 
symmetric layouts, proper content sizing, and a consistent color scheme.
"""
import asyncio
import sys
import time
import random
from typing import Optional, List, Dict, Any, Callable, Awaitable, Tuple, Set
from enum import Enum
from pathlib import Path
import textwrap

from rich.console import Console, Group
from rich.panel import Panel
from rich.syntax import Syntax
from rich.progress import Progress, SpinnerColumn, TextColumn, BarColumn, TimeElapsedColumn
from rich.table import Table
from rich.live import Live
from rich.text import Text
from rich.layout import Layout
from rich.tree import Tree
from rich.spinner import Spinner
from rich.markdown import Markdown
from rich.columns import Columns
from rich import box
from rich.style import Style
from rich.align import Align

from angela.api.intent import get_advanced_task_plan_class, get_plan_step_type_enum
from angela.utils.logging import get_logger
from angela.constants import RISK_LEVELS

# ════════════════════════════════════════════════
# Consistent box style for visual unity
# ════════════════════════════════════════════════
DEFAULT_BOX = box.ROUNDED

# ════════════════════════════════════════════════
# Cohesive color palette with consistent theme
# ════════════════════════════════════════════════

COLOR_PALETTE = {
    "border": "#ff0055",           # Red border for all panels
    "text": "#00c8ff",             # Blue text for panel content
    "confirmation": "#8a2be2",     # Purple for confirmation panels
    "confirmation_text": "#ff0055", # Red text for confirmation panels
    "success": "#00ff99",          # Success green
    "warning": "#ffcc00",          # Warning yellow
    "error": "#ff3355",            # Error red
    "info": "#00c8ff",             # Information blue
    "subtle": "#6c7280",           # Subdued color for less important elements
    "white": "#ffffff",            # White for high-contrast elements
}

# ════════════════════════════════════════════════
# Simple ASCII decorators for visual markers
# ════════════════════════════════════════════════

ASCII_DECORATIONS = {
    "command": "⚡",
    "output": "◈",
    "error": "⚠",
    "confirmation": "◈",
    "success": "✓",
    "warning": "⚠",
}

# Get risk level names mapping for display
RISK_LEVEL_NAMES = {v: k for k, v in RISK_LEVELS.items()}

# Risk styling with consistent color scheme
RISK_COLORS = {
    RISK_LEVELS["SAFE"]: COLOR_PALETTE["success"],
    RISK_LEVELS["LOW"]: COLOR_PALETTE["info"],
    RISK_LEVELS["MEDIUM"]: COLOR_PALETTE["warning"],
    RISK_LEVELS["HIGH"]: COLOR_PALETTE["error"],
    RISK_LEVELS["CRITICAL"]: COLOR_PALETTE["border"],
}

RISK_ICONS = {
    RISK_LEVELS["SAFE"]: "✓",
    RISK_LEVELS["LOW"]: "⚡",
    RISK_LEVELS["MEDIUM"]: "⚠",
    RISK_LEVELS["HIGH"]: "❗",
    RISK_LEVELS["CRITICAL"]: "⛔",
}

AdvancedTaskPlan = get_advanced_task_plan_class()
PlanStepType = get_plan_step_type_enum()

_console = Console(record=True, width=100)

logger = get_logger(__name__)

class OutputType(Enum):
    """Types of command output."""
    STDOUT = "stdout"
    STDERR = "stderr"
    INFO = "info"
    SUCCESS = "success"
    WARNING = "warning"
    ERROR = "error"
    PROGRESS = "progress"

class TerminalFormatter:
    """
    Rich terminal formatter with responsive layout and consistent styling.
    """

    # Philosophy quotes for loading screens
    PHILOSOPHY_QUOTES = [
        # Aristotle quotes
        "We are what we repeatedly do. Excellence, then, is not an act, but a habit. - Aristotle",
        "The whole is greater than the sum of its parts. - Aristotle",
        "Knowing yourself is the beginning of all wisdom. - Aristotle",
        "It is the mark of an educated mind to be able to entertain a thought without accepting it. - Aristotle",
        "Happiness depends upon ourselves. - Aristotle",
        
        # Socrates quotes
        "The unexamined life is not worth living. - Socrates",
        "I know that I am intelligent, because I know that I know nothing. - Socrates",
        "The secret of change is to focus all of your energy not on fighting the old, but on building the new. - Socrates",
        "Be kind, for everyone you meet is fighting a hard battle. - Socrates",
        "Wonder is the beginning of wisdom. - Socrates",
        
        # Plato quotes
        "At the touch of love everyone becomes a poet. - Plato",
        "We can easily forgive a child who is afraid of the dark; the real tragedy of life is when men are afraid of the light. - Plato",
        "Be kind, for everyone you meet is fighting a harder battle. - Plato",
        "The measure of a man is what he does with power. - Plato",
        "Wise men speak because they have something to say; fools because they have to say something. - Plato",
        
        # Sun Tzu quotes
        "Appear weak when you are strong, and strong when you are weak. - Sun Tzu",
        "The supreme art of war is to subdue the enemy without fighting. - Sun Tzu",
        "Let your plans be dark and impenetrable as night, and when you move, fall like a thunderbolt. - Sun Tzu",
        "If you know the enemy and know yourself, you need not fear the result of a hundred battles. - Sun Tzu",
        "Victorious warriors win first and then go to war, while defeated warriors go to war first and then seek to win. - Sun Tzu",
        
        # Hypatia quotes
        "Reserve your right to think, for even to think wrongly is better than not to think at all. - Hypatia",
        "Life is an unfoldment, and the further we travel the more truth we can comprehend. - Hypatia",
        "To teach superstitions as truth is a most terrible thing. - Hypatia",
        "All formal dogmatic religions are fallacious and must never be accepted by self-respecting persons as final. - Hypatia",
        
        # Sextus Empiricus quotes
        "For every argument, there is a counter-argument of equal weight. - Sextus Empiricus",
        "The wise man suspends judgment; he recognizes that nothing is certain. - Sextus Empiricus",
        "Appearances are our only guide in life. - Sextus Empiricus",
        "The goal of the skeptic is tranquility of mind. - Sextus Empiricus",
        
        # Pythagoras quotes
        "The highest form of pure thought is in mathematics. - Pythagoras",
        "Number is the ruler of forms and ideas, and the cause of gods and demons. - Pythagoras",
        "Concern should drive us into action and not into a depression. - Pythagoras",
        "Above all things, reverence yourself. - Pythagoras",
        
        # Xenophanes quotes
        "If cattle and horses had hands, they would draw the forms of gods like cattle and horses. - Xenophanes",
        "There is one god, greatest among gods and men, similar to mortals neither in shape nor in thought. - Xenophanes",
        "The gods did not reveal all things to men at the start; but as time goes on, by searching, they discover more. - Xenophanes",
        "Men create the gods in their own image. - Xenophanes",
        
        # Additional philosophical quotes
        "The only true wisdom is in knowing you know nothing. - Socrates",
        "Man is the measure of all things. - Protagoras",
        "I think, therefore I am. - René Descartes",
        "He who has a why to live can bear almost any how. - Friedrich Nietzsche",
        "One cannot step twice in the same river. - Heraclitus",
        "The function of prayer is not to influence God, but rather to change the nature of the one who prays. - Søren Kierkegaard",
        "What is rational is actual and what is actual is rational. - G.W.F. Hegel"
    ]
    
    def __init__(self):
        """Initialize the terminal formatter."""
        self._console = Console()
        self._logger = logger
        self._active_displays = set()
        
    def _get_quantum_vortex_spinner(self, elapsed: float) -> Text:
        """Create a mesmerizing quantum vortex spinner animation."""
        import math
        spinner_text = Text()
        
        # Outer vortex ring with color cycling
        outer_symbols = ["◜", "◠", "◝", "◞", "◡", "◟"]
        outer_idx = int(elapsed * 6) % len(outer_symbols)
        outer_char = outer_symbols[outer_idx]
        
        # Color cycle through spectrum
        hue = int(elapsed * 36) % 360
        # Create RGB colors that cycle
        r = int(abs(math.sin(hue/60)) * 255)
        g = int(abs(math.sin((hue+120)/60)) * 255)
        b = int(abs(math.sin((hue+240)/60)) * 255)
        color_hex = f"#{r:02x}{g:02x}{b:02x}"
        
        # Inner particle with opposite rotation
        inner_symbols = ["•", "◦", "●", "○", "◎", "◉"]
        inner_idx = int(elapsed * 8) % len(inner_symbols)
        inner_idx_reverse = (len(inner_symbols) - 1 - inner_idx)  # Reverse direction
        inner_char = inner_symbols[inner_idx_reverse]
        
        # Pulsing effect for center particle
        pulse_size = 1 + 0.5 * math.sin(elapsed * 3)
        if pulse_size > 1.25:
            center_style = "bold bright_white"
        else:
            center_style = "dim white"
        
        # Assemble the spinner components
        spinner_text.append(outer_char, style=color_hex)
        spinner_text.append(inner_char, style=center_style)
        
        # Quantum particle trails
        particle_pos = int(elapsed * 5) % 3
        trail = " " * particle_pos + "∴" + " " * (2 - particle_pos)
        spinner_text.append(trail, style=COLOR_PALETTE["info"])
        
        return spinner_text
    
    def _get_elemental_cascade_spinner(self, elapsed: float) -> Text:
        """Create a spinner that cycles through elemental themes."""
        import math
        spinner_text = Text()
        
        # Determine current element based on time
        element_cycle = int(elapsed * 2) % 4  # Changes every 0.5 seconds
        
        # Element-specific animations
        if element_cycle == 0:  # Fire
            fire_symbols = ["🔥", "🔥", "🔥", "🔥", "💥", "✨", "🔥", "🔥"]
            fire_idx = int(elapsed * 12) % len(fire_symbols)
            
            # Flame intensity changes
            flame_chars = ["═", "╪", "╫", "╬", "╬", "╫", "╪"]
            flame_idx = int(elapsed * 14) % len(flame_chars)
            
            spinner_text.append(fire_symbols[fire_idx]) # Appending a plain character
            spinner_text.append(flame_chars[flame_idx], style=COLOR_PALETTE["border"])
            spinner_text.append("~", style=COLOR_PALETTE["warning"])
            
        elif element_cycle == 1:  # Water
            water_symbols = ["≈", "≋", "≈", "∽", "∿", "≈"]
            water_idx = int(elapsed * 12) % len(water_symbols)
            
            # Wave effect
            wave_level = int(2 + 2 * math.sin(elapsed * 6))
            waves = "~" * wave_level
            
            spinner_text.append(water_symbols[water_idx], style=COLOR_PALETTE["info"])
            spinner_text.append(waves, style=COLOR_PALETTE["info"])
            spinner_text.append("○", style=COLOR_PALETTE["info"])
            
        elif element_cycle == 2:  # Earth
            earth_symbols = ["◦", "•", "●", "◎", "◉", "⦿", "◉", "◎", "●", "•"]
            earth_idx = int(elapsed * 10) % len(earth_symbols)
            
            # Growth effect
            growth = [".", "․", "‥", "…", "⁘", "⁙"]
            growth_idx = int(elapsed * 6) % len(growth)
            
            spinner_text.append(earth_symbols[earth_idx], style=COLOR_PALETTE["success"])
            spinner_text.append(growth[growth_idx], style=COLOR_PALETTE["success"])
            spinner_text.append("⏣", style=COLOR_PALETTE["success"])
            
        else:  # Air
            air_symbols = ["≋", "≈", "≋", "≈", "≋", "≈"]
            air_idx = int(elapsed * 8) % len(air_symbols)
            
            # Wind effect
            wind_dir = int(elapsed * 4) % 2
            if wind_dir == 0:
                wind = "»»»"
            else:
                wind = "«««"
                
            spinner_text.append(air_symbols[air_idx], style=COLOR_PALETTE["white"])
            spinner_text.append(wind, style=COLOR_PALETTE["white"])
            spinner_text.append("◌", style=COLOR_PALETTE["info"])
        
        return spinner_text
    
    def _get_interstellar_warp_spinner(self, elapsed: float) -> Text:
        """Create a mind-blowing warp drive animation effect."""
        import math
        spinner_text = Text()
        
        # Warp ship core with pulsing energy
        energy_level = int(3 + 3 * math.sin(elapsed * 8))
        core_symbols = ["▮", "▰", "█", "▰", "▮", "▯", "▮", "▰", "█"]
        core_idx = int(elapsed * 12) % len(core_symbols)
        core_char = core_symbols[core_idx]
        
        # Warp field effect with varying lengths based on warp speed
        warp_factor = 1 + int(elapsed * 10) % 9  # Warp factors 1-9
        warp_speed = min(4, int(1 + warp_factor/2))  # Max length of 4
        
        # Center of animation
        spinner_text.append("=", style=COLOR_PALETTE["info"])
        spinner_text.append(core_char * energy_level, style=COLOR_PALETTE["warning"])
        spinner_text.append("=", style=COLOR_PALETTE["info"])
        
        # Starfield effect - stars zooming past at different speeds
        star_positions = []
        for i in range(5):  # Generate 5 stars
            # Each star moves at different speeds
            pos = (elapsed * (5 + i)) % 15
            intensity = min(1.0, 15 - pos) / 1.0  # Fade based on position
            
            if intensity > 0.7:
                style = COLOR_PALETTE["white"]
            elif intensity > 0.4:
                style = COLOR_PALETTE["text"]
            else:
                style = COLOR_PALETTE["subtle"]
                
            # Convert position to integer for display
            pos_int = int(pos)
            
            # Star character depends on position (moving away = smaller)
            if pos_int < 3:
                star = "*"
            elif pos_int < 7:
                star = "·"
            else:
                star = "."
                
            # Add to positions list
            star_positions.append((pos_int, star, style))
        
        # Sort stars by position for layering
        star_positions.sort()
        
        # Create starfield
        starfield_markup_list = [""] * 15  # Initialize empty spaces with placeholder
        for pos, star, style in star_positions:
            if 0 <= pos < 15:  # Ensure within bounds
                # Store as markup string in the list
                starfield_markup_list[pos] = f"[{style}]{star}[/{style}]"
        
        # Add leading stars
        for i in range(warp_speed):
            # Join the markup strings from the list for the current segment
            starfield_segment_markup = "".join(starfield_markup_list[i*3:(i+1)*3])
            if starfield_segment_markup.strip():  # Only add if there's visible content
                # Append the composed markup string, ensuring it's parsed by Text.from_markup
                spinner_text.append(Text.from_markup(starfield_segment_markup))
        
        # Add warp drive energy fluctuation
        fluctuation = int(elapsed * 20) % 3
        if fluctuation == 0:
            spinner_text.append("⚡", style=COLOR_PALETTE["info"])
        elif fluctuation == 1:
            spinner_text.append("⚡", style=COLOR_PALETTE["confirmation"])
        else:
            spinner_text.append("⚡", style=COLOR_PALETTE["warning"])
        
        return spinner_text
    
    def _get_random_spinner(self, elapsed: float) -> Text:
        """Get a random spinner based on object ID determinism."""
        import random
        
        # We'll use the hash of the elapsed time's integer part to select a spinner,
        # but only hash it once at the beginning of a loading session
        if not hasattr(self, '_current_spinner_choice'):
            # Initialize a random spinner for this loading session
            self._current_spinner_choice = random.randint(1, 3)
            self._logger.debug(f"Selected spinner animation: {self._current_spinner_choice}")
        
        # Use the selected spinner
        if self._current_spinner_choice == 1:
            return self._get_quantum_vortex_spinner(elapsed)
        elif self._current_spinner_choice == 2:
            return self._get_elemental_cascade_spinner(elapsed)
        else:
            return self._get_interstellar_warp_spinner(elapsed)

    def print_command(self, command: str, title: Optional[str] = None) -> None:
        """
        Display a command with syntax highlighting.
        
        Args:
            command: The command to display
            title: Optional title for the panel
        """
        title = title or f"{ASCII_DECORATIONS['command']} Command {ASCII_DECORATIONS['command']}"
        
        # Create a syntax object with proper styling
        syntax = Syntax(
            command, 
            "bash", 
            theme="vim", 
            word_wrap=True,
            background_color="default"
        )
        
        # Create a panel with the syntax
        panel = Panel(
            syntax,
            title=f"[bold {COLOR_PALETTE['border']}]{title}[/bold {COLOR_PALETTE['border']}]",
            border_style=COLOR_PALETTE["border"],
            box=DEFAULT_BOX,
            expand=False,  # Don't expand beyond content
            padding=(1, 2)
        )
        
        self._console.print("")
        self._console.print(panel)
    
    def print_output(
        self, 
        output: str, 
        output_type: OutputType = OutputType.STDOUT,
        title: Optional[str] = None
    ) -> None:
        """
        Display command output with appropriate formatting.
        
        Args:
            output: The output text
            output_type: Type of output
            title: Optional title for the panel
        """
        if not output:
            return
            
        # Set styling based on output type
        if output_type == OutputType.STDERR or output_type == OutputType.ERROR:
            style = COLOR_PALETTE["error"]
            title = title or f"{ASCII_DECORATIONS['error']} Error {ASCII_DECORATIONS['error']}"
        elif output_type == OutputType.WARNING:
            style = COLOR_PALETTE["warning"]
            title = title or f"{ASCII_DECORATIONS['warning']} Warning {ASCII_DECORATIONS['warning']}"
        elif output_type == OutputType.SUCCESS:
            style = COLOR_PALETTE["success"]
            title = title or f"{ASCII_DECORATIONS['success']} Success {ASCII_DECORATIONS['success']}"
        elif output_type == OutputType.INFO:
            style = COLOR_PALETTE["info"]
            title = title or f"{ASCII_DECORATIONS['info']} Info {ASCII_DECORATIONS['info']}"
        else:  # Default for STDOUT
            style = COLOR_PALETTE["text"]
            title = title or f"{ASCII_DECORATIONS['output']} Output {ASCII_DECORATIONS['output']}"
        
        # Clean up the output - remove any trailing blank lines
        cleaned_output = output.rstrip()
        
        # Create panel with output
        # Use the consistent color scheme - red border, blue text
        text = Text(cleaned_output, style=COLOR_PALETTE["text"])
        
        panel = Panel(
            text,
            title=f"[bold {style}]{title}[/bold {style}]",
            border_style=COLOR_PALETTE["border"],  # Always use red for border
            box=DEFAULT_BOX,
            expand=False,  # Don't expand beyond content
            padding=(1, 2)
        )
        
        self._console.print("")
        self._console.print(panel)
    
    def print_error_analysis(self, analysis: Dict[str, Any]) -> None:
        """
        Display error analysis with fix suggestions.
        
        Args:
            analysis: The error analysis dictionary
        """
        # Create a table for the error analysis 
        table = Table(
            title=f"[bold {COLOR_PALETTE['error']}]Error Analysis[/bold {COLOR_PALETTE['error']}]",
            box=DEFAULT_BOX,
            border_style=COLOR_PALETTE["border"],  # Consistent red border
            highlight=True,
            expand=False
        )
        
        table.add_column("Aspect", style=COLOR_PALETTE["confirmation"], justify="right")
        table.add_column("Details", style=COLOR_PALETTE["text"])  # Consistent blue text
        
        # Add error summary
        error_text = Text(analysis.get("error_summary", "Unknown error"), style=COLOR_PALETTE["error"])
        table.add_row("Error", error_text)
        
        # Add possible cause
        table.add_row("Possible Cause", analysis.get("possible_cause", "Unknown"))
        
        # Add command issues
        if analysis.get("command_issues"):
            issues = "\n".join(f"• {issue}" for issue in analysis["command_issues"])
            table.add_row("Command Issues", issues)
        
        # Add file issues
        if analysis.get("file_issues"):
            file_issues = []
            for issue in analysis["file_issues"]:
                path = issue.get("path", "unknown")
                if "suggestion" in issue:
                    file_issues.append(f"• {path}: {issue['suggestion']}")
                if "similar_files" in issue:
                    similar = ", ".join(issue["similar_files"])
                    file_issues.append(f"  Did you mean: {similar}?")
            
            if file_issues:
                table.add_row("File Issues", "\n".join(file_issues))
        
        # Display the table
        self._console.print("")
        self._console.print(table)
        
        # Display fix suggestions if available
        if analysis.get("fix_suggestions"):
            suggestions = analysis["fix_suggestions"]
            if suggestions:
                # Create a suggestions panel with consistent styling
                suggestion_text = []
                for i, suggestion in enumerate(suggestions, 1):
                    suggestion_text.append(f"[{COLOR_PALETTE['text']}]• {suggestion}[/{COLOR_PALETTE['text']}]")
                
                self._console.print(Panel(
                    "\n".join(suggestion_text),
                    title=f"[bold {COLOR_PALETTE['success']}]Fix Suggestions[/bold {COLOR_PALETTE['success']}]",
                    border_style=COLOR_PALETTE["border"],  # Consistent red border
                    box=DEFAULT_BOX,
                    expand=False,
                    padding=(1, 2)
                ))

    async def display_pre_confirmation_info(
        self,
        command: str,
        risk_level: int,
        risk_reason: str,
        impact: Dict[str, Any],
        explanation: Optional[str] = None,
        preview: Optional[str] = None,
        confidence_score: Optional[float] = None,
        execution_time: Optional[float] = None
    ) -> None:
        """
        Display a symmetrical and properly aligned pre-confirmation layout.
        
        Args:
            command: The command to be executed
            risk_level: Risk level (0-4)
            risk_reason: Reason for the risk assessment
            impact: Impact analysis dictionary
            explanation: Optional explanation of the command
            preview: Optional preview of command execution
            confidence_score: Optional AI confidence score (0-1)
            execution_time: Optional execution time if this is post-execution
        """
        # Get console width for proper layout
        console_width = self._console.width
        
        # Risk level styling
        risk_name = RISK_LEVEL_NAMES.get(risk_level, "UNKNOWN")
        risk_icon = RISK_ICONS.get(risk_level, "⚠")
        risk_color = RISK_COLORS.get(risk_level, COLOR_PALETTE["warning"])
        
        # Calculate main panel width - make sure it's centered
        main_panel_width = min(console_width - 10, 80)  # Max 80 chars or less depending on terminal
        
        # 1. Command panel (top)
        command_panel = Panel(
            Syntax(command, "bash", theme="vim", word_wrap=True),
            title=f"[bold {risk_color}]{risk_icon} Execute [{risk_name} Risk][/bold {risk_color}]",
            border_style=COLOR_PALETTE["border"],
            box=DEFAULT_BOX,
            width=main_panel_width,
            padding=(1, 2)
        )
        
        # 2. Explanation and confidence score panels (side by side)
        explanation_text = explanation or "No explanation available for this command."
        explanation_panel = Panel(
            Text(explanation_text, style=COLOR_PALETTE["text"]),
            title=f"[bold {COLOR_PALETTE['text']}]✧ Command Insight ✧[/bold {COLOR_PALETTE['text']}]",
            border_style=COLOR_PALETTE["border"],
            box=DEFAULT_BOX,
            width=main_panel_width // 2 - 1,  # Divide available space
            padding=(1, 2)
        )
        
        # Confidence panel creation
        if confidence_score is not None:
            confidence_stars = int(confidence_score * 5)
            confidence_display = "★" * confidence_stars + "☆" * (5 - confidence_stars)
            
            if confidence_score > 0.8:
                confidence_color = COLOR_PALETTE["success"]
            elif confidence_score > 0.6:
                confidence_color = COLOR_PALETTE["info"]
            else:
                confidence_color = COLOR_PALETTE["error"]
            
            confidence_panel = Panel(
                Group(
                    Text("Score:", style=f"bold {COLOR_PALETTE['text']}", justify="center"),
                    Text(f"{confidence_score:.2f}", style=f"bold {confidence_color}", justify="center"),
                    Text(confidence_display, style=confidence_color, justify="center"),
                    Text("", justify="center"),  # Empty line for spacing
                    Text("(AI confidence in", style="dim", justify="center"),
                    Text("command accuracy)", style="dim", justify="center")
                ),
                title=f"[bold {COLOR_PALETTE['text']}]✧ AI Confidence ✧[/bold {COLOR_PALETTE['text']}]",
                border_style=COLOR_PALETTE["border"],
                box=DEFAULT_BOX,
                width=main_panel_width // 2 - 1,  # Divide available space
                padding=(1, 2)
            )
        else:
            confidence_panel = Panel(
                Text("No confidence score available.", style="dim", justify="center"),
                title=f"[bold {COLOR_PALETTE['text']}]✧ AI Confidence ✧[/bold {COLOR_PALETTE['text']}]",
                border_style=COLOR_PALETTE["border"],
                box=DEFAULT_BOX,
                width=main_panel_width // 2 - 1,
                padding=(1, 2)
            )
        
        # 3. Preview panel (if available)
        if preview:
            preview_panel = Panel(
                Text(preview, style=COLOR_PALETTE["text"]),
                title=f"[bold {COLOR_PALETTE['text']}]⚡ Command Preview ⚡[/bold {COLOR_PALETTE['text']}]",
                border_style=COLOR_PALETTE["border"],
                box=DEFAULT_BOX,
                width=main_panel_width,
                padding=(1, 2)
            )
        
        # 4. Risk assessment panel
        impact_summary = []
        if impact.get("operations"):
            ops = ", ".join(impact["operations"])
            impact_summary.append(f"Operations: {ops}")
        
        if impact.get("affected_files"):
            files = ", ".join(Path(f).name for f in impact["affected_files"])
            impact_summary.append(f"Files: {files}")
        
        if impact.get("affected_dirs"):
            dirs = ", ".join(Path(d).name for d in impact["affected_dirs"])
            impact_summary.append(f"Directories: {dirs}")
        
        impact_text = "\n".join(impact_summary) if impact_summary else "No detailed impact available."
        
        risk_panel = Panel(
            Group(
                Text(f"Level: {risk_name}", style=risk_color),
                Text(f"Reason: {risk_reason}", style=COLOR_PALETTE["text"]),
                Text("", justify="center"),  # Empty line for spacing
                Text("Impact Assessment:", style=f"bold {COLOR_PALETTE['text']}"),
                Text(impact_text, style=COLOR_PALETTE["text"])
            ),
            title=f"[bold {risk_color}]⚠ Risk Assessment[/bold {risk_color}]",
            border_style=COLOR_PALETTE["border"],
            box=DEFAULT_BOX,
            width=main_panel_width,
            padding=(1, 2)
        )
        
        # Now actually display everything in the right order and centered properly
        
        # 1. Display command panel centered
        self._console.print()
        self._console.print(Align.center(command_panel))
        
        # 2. Display explanation and confidence panels side by side
        columns = Columns([explanation_panel, confidence_panel], equal=False, padding=0)
        self._console.print(Align.center(columns, width=main_panel_width + 2))  # +2 for borders
        
        # 3. Display preview panel if available
        if preview:
            self._console.print(Align.center(preview_panel))
        
        # 4. Display risk panel
        self._console.print(Align.center(risk_panel))
        self._console.print()  # Add some space at the end

    async def display_inline_confirmation(
        self,
        prompt_text: str = "Proceed with execution?"
    ) -> bool:
        """
        Display an inline confirmation prompt and get user input.
        
        Args:
            prompt_text: The confirmation prompt text
            
        Returns:
            True if confirmed, False otherwise
        """
        # Create a confirmation prompt with consistent styling
        # Purple background with red text as requested
        panel_content = Group(
            Text(prompt_text, style=COLOR_PALETTE["confirmation_text"], justify="center"),
            Text("", justify="center"),  # Empty line for spacing
            Text.from_markup(f"([bold {COLOR_PALETTE['success']}]y[/bold {COLOR_PALETTE['success']}]/[bold {COLOR_PALETTE['error']}]n[/bold {COLOR_PALETTE['error']}])", justify="center")
        )
        
        confirmation_panel = Panel(
            panel_content,
            title=f"[bold {COLOR_PALETTE['confirmation']}]{ASCII_DECORATIONS['confirmation']} Awaiting Confirmation {ASCII_DECORATIONS['confirmation']}[/bold {COLOR_PALETTE['confirmation']}]",
            border_style=COLOR_PALETTE["confirmation"],  # Purple border for confirmation
            box=DEFAULT_BOX,
            expand=False,
            padding=(1, 2)
        )
        
        self._console.print("")
        self._console.print(confirmation_panel)
        
        # Get the user's response with consistent styling
        self._console.print(f"[bold {COLOR_PALETTE['confirmation']}]>>> [/bold {COLOR_PALETTE['confirmation']}]", end="")
        response = input().strip().lower()
        
        # Consider empty response or y/yes as "yes"
        if not response or response in ("y", "yes"):
            return True
        
        # Everything else is "no"
        return False

    async def display_execution_timer(
        self,
        command: str,
        with_philosophy: bool = True,
        interactive: bool = False  # New parameter for interactive commands
    ) -> Tuple[str, str, int, float]:
        """
        Display a command execution timer with philosophy quotes.
        
        Args:
            command: The command being executed
            with_philosophy: Whether to display philosophy quotes
            interactive: Whether this is an interactive command that needs direct terminal access
            
        Returns:
            Tuple of (stdout, stderr, return_code, execution_time)
        """
        from angela.utils.command_utils import is_interactive_command, display_command_recommendation
        
        is_interactive, base_cmd = is_interactive_command(command)
        if is_interactive:
            # Display recommendation for interactive commands
            display_command_recommendation(command)
            
            # Return dummy result without execution
            execution_time = 0.1
            return ("", "", 0, execution_time)        
        
        
        import random
        import time
        import asyncio
        from rich.live import Live
        from rich.panel import Panel
        from rich.text import Text
        from rich.console import Group
        
        # Ensure no active live displays
        self._ensure_no_active_live()
        
        # Reset spinner choice for new execution session
        if hasattr(self, '_current_spinner_choice'):
            delattr(self, '_current_spinner_choice')
        
        # Check if this is an interactive command that should be recommended instead of executed
        interactive_commands = [
            "vim", "vi", "nano", "emacs", "pico", "less", "more", 
            "top", "htop", "btop", "iotop", "iftop", "nmon", "glances", "atop",
            "ping", "traceroute", "mtr", "tcpdump", "wireshark", "tshark", "ngrep",
            "tail", "watch", "journalctl", "dmesg", "ssh", "telnet", "nc", "netcat",
            "mysql", "psql", "sqlite3", "mongo", "redis-cli", "gdb", "lldb", "pdb",
            "tmux", "screen"
        ]
        
        base_cmd = command.split()[0] if command.split() else ""
        should_recommend = base_cmd in interactive_commands
        
        # Special cases with flags
        if not should_recommend:
            if base_cmd == "ping" and "-c" not in command:
                should_recommend = True
            elif base_cmd == "tail" and "-f" in command:
                should_recommend = True
            elif base_cmd == "journalctl" and "-f" in command:
                should_recommend = True
        
        if should_recommend:
            # Provide a recommendation instead of execution for interactive commands
            from rich.panel import Panel
            
            # Create a recommendation message
            recommendation = f"""
    [bold cyan]Interactive Command Detected:[/bold cyan]
    
    Angela cannot directly execute terminal-interactive commands like {base_cmd}.
    You can run this command yourself by typing:
    
        [bold green]{command}[/bold green]
    
    This will launch {base_cmd} in your terminal.
    """
            
            # Print the recommendation
            self._console.print(Panel(
                recommendation,
                title="[bold cyan]Command Recommendation[/bold cyan]",
                border_style=COLOR_PALETTE["border"],
                box=DEFAULT_BOX,
                expand=False
            ))
            
            # Return empty results as if the command was executed
            execution_time = 0.1
            return ("", "", 0, execution_time)
        
        # Normal execution for non-interactive commands (rest of the method)
        
        # Original implementation after this point...
        start_time = time.time()
        
        # Choose a random philosophy quote
        quote = random.choice(self.PHILOSOPHY_QUOTES) if with_philosophy else ""
        
        # Create a layout for execution display
        def get_layout():
            elapsed = time.time() - start_time
            
            # Get a random but consistent spinner for this execution session
            spinner = self._get_random_spinner(elapsed)
            
            # Add execution message
            spinner_with_text = Text()
            spinner_with_text.append(spinner)
            spinner_with_text.append(" ")
            spinner_with_text.append(f"{elapsed:.2f}s", style=f"bold {COLOR_PALETTE['text']}")
            spinner_with_text.append(" - Executing command...")
            
            if with_philosophy:
                # For the philosophy quote
                quote_text = Text(quote, style=f"italic {COLOR_PALETTE['text']}")
                
                # Add an empty line for spacing
                spacer = Text("")
                
                # Group them together with proper spacing
                content = Group(quote_text, spacer, spinner_with_text)
            else:
                content = spinner_with_text
            
            panel = Panel(
                content,
                title="Command Execution",
                border_style=COLOR_PALETTE["border"],  # Consistent red border
                box=DEFAULT_BOX,
                padding=(1, 2)
            )
            
            return panel
        
        if interactive:
            # For interactive commands, don't capture stdout/stderr
            # Just display loading initially, then let the command take over the terminal
            try:
                with Live(get_layout(), refresh_per_second=20, console=self._console) as live:
                    # Brief display of loading before handing over to interactive command
                    await asyncio.sleep(0.5)
                    live.stop()
                    
                    # Use create_subprocess_shell without redirecting stdout/stderr
                    # This is the key change - allows direct terminal interaction
                    process = await asyncio.create_subprocess_shell(
                        command
                        # No stdout/stderr redirection for interactive mode
                    )
                    
                    # Wait for the process to complete
                    return_code = await process.wait()
                    execution_time = time.time() - start_time
                    
                    # Create a completion panel - KEEPING the "Angela Initialized" title
                    execution_time_text = Text()
                    execution_time_text.append("Clocked in ", style=COLOR_PALETTE["text"])
                    execution_time_text.append(f"{execution_time:.6f}", style="red")
                    execution_time_text.append("s", style=COLOR_PALETTE["text"])
                    execution_time_text.justify = "center"
                    
                    completed_panel = Panel(
                        execution_time_text,
                        title=f"[bold {COLOR_PALETTE['text']}]✓ Angela Initialized ✓[/bold {COLOR_PALETTE['text']}]",
                        border_style=COLOR_PALETTE["border"],
                        box=DEFAULT_BOX,
                        expand=False,
                        padding=(1, 2)
                    )
                    
                    # Create a new live display for completion message
                    with Live(completed_panel, refresh_per_second=1, console=self._console) as completion_live:
                        await asyncio.sleep(0.5)
                    
                    # Return empty stdout/stderr since they were directed to terminal
                    return ("", "", return_code, execution_time)
            except Exception as e:
                self._logger.error(f"Error in interactive execution: {str(e)}")
                return ("", f"Error: {str(e)}", -1, time.time() - start_time)
        else:
            # Original implementation for non-interactive commands
            # Use asyncio.create_subprocess_shell to execute the command
            process = await asyncio.create_subprocess_shell(
                command,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE
            )
            
            # Collect output
            stdout_chunks = []
            stderr_chunks = []
            
            # Set up tasks to read output
            async def read_stream(stream, is_stdout: bool):
                while True:
                    line = await stream.readline()
                    if not line:
                        break
                        
                    try:
                        line_str = line.decode('utf-8', errors='replace')
                        
                        # Store the output
                        if is_stdout:
                            stdout_chunks.append(line_str)
                        else:
                            stderr_chunks.append(line_str)
                            
                    except Exception as e:
                        self._logger.error(f"Error processing output: {str(e)}")
            
            # Create tasks for stdout and stderr
            stdout_task = asyncio.create_task(read_stream(process.stdout, True))
            stderr_task = asyncio.create_task(read_stream(process.stderr, False))
            
            # Display the live progress with stunning visuals
            try:
                with Live(get_layout(), refresh_per_second=20, console=self._console) as live:
                    # Wait for the command to complete while updating the display
                    return_code = await process.wait()
                    
                    # Wait for the streams to complete
                    await stdout_task
                    await stderr_task
                    
                    execution_time = time.time() - start_time
                    
                    # Create a visually stunning completion panel
                    execution_time_text = Text()
                    execution_time_text.append("Clocked in ", style=COLOR_PALETTE["text"])
                    execution_time_text.append(f"{execution_time:.6f}", style="red")  # Different color for numbers
                    execution_time_text.append("s", style=COLOR_PALETTE["text"])
                    
                    # Center the text
                    execution_time_text.justify = "center"
                    
                    completed_panel = Panel(
                        execution_time_text,
                        title=f"[bold {COLOR_PALETTE['text']}]✓ Angela Initialized ✓[/bold {COLOR_PALETTE['text']}]",
                        border_style=COLOR_PALETTE["border"],
                        box=DEFAULT_BOX,
                        expand=False,
                        padding=(1, 2)
                    )
                    
                    live.update(completed_panel)
                    
                    # Brief pause to show completion
                    await asyncio.sleep(0.5)
            except Exception as e:
                self._logger.error(f"Error in execution timer: {str(e)}")
                # Ensure we still wait for the process
                if process.returncode is None: # Check if process might still be running
                    try:
                        # Wait for process with a timeout to avoid hanging indefinitely
                        await asyncio.wait_for(process.wait(), timeout=5.0) 
                        return_code = process.returncode if process.returncode is not None else -1
                    except asyncio.TimeoutError:
                        self._logger.error("Timeout waiting for process to complete after error.")
                        if process.returncode is None: # if still none after timeout, try to kill
                            try:
                                process.kill()
                                await process.wait() # ensure it's reaped
                            except ProcessLookupError:
                                pass # process might have already exited
                            except Exception as kill_e:
                                self._logger.error(f"Error trying to kill process: {kill_e}")
                        return_code = -1 
                    except Exception as proc_e:
                        self._logger.error(f"Further error waiting for process: {proc_e}")
                        return_code = -1
                elif process.returncode is not None: # Process already finished, just get its code
                    return_code = process.returncode
                else: # Fallback if process object is in an unexpected state
                    return_code = -1
    
                # Wait for the streams to complete, even in error cases
                # Use try-except for each to ensure one doesn't prevent the other
                try:
                    await asyncio.wait_for(stdout_task, timeout=2.0)
                except asyncio.TimeoutError:
                    self._logger.error("Timeout waiting for stdout_task to complete after error.")
                except Exception as stream_e:
                    self._logger.error(f"Error waiting for stdout_task: {stream_e}")
                
                try:
                    await asyncio.wait_for(stderr_task, timeout=2.0)
                except asyncio.TimeoutError:
                    self._logger.error("Timeout waiting for stderr_task to complete after error.")
                except Exception as stream_e:
                    self._logger.error(f"Error waiting for stderr_task: {stream_e}")
                
                # Recalculate execution_time up to the point of error handling completion
                execution_time = time.time() - start_time
            
            # Return the results
            return (
                "".join(stdout_chunks),
                "".join(stderr_chunks),
                return_code if isinstance(return_code, int) else -1, # Ensure return_code is an int
                execution_time
            )


    async def display_loading_timer(
        self,
        message: str,
        with_philosophy: bool = True
    ) -> None:
        """
        Display a loading timer with optional philosophy quotes.
        
        Args:
            message: The loading message to display
            with_philosophy: Whether to display philosophy quotes
        """
        import random
        import time
        import asyncio
        from rich.live import Live
        from rich.panel import Panel
        from rich.text import Text
        from rich.console import Group
        
        # Ensure no active live displays
        self._ensure_no_active_live()
        
        # Reset spinner choice for new loading session
        if hasattr(self, '_current_spinner_choice'):
            delattr(self, '_current_spinner_choice')
        
        start_time = time.time()
        
        # Choose a random philosophy quote
        quote = random.choice(self.PHILOSOPHY_QUOTES) if with_philosophy else ""
        
        # Create a layout function that properly handles the spinner
        def get_layout():
            elapsed = time.time() - start_time
            
            # Get a random but consistent spinner for this loading session
            spinner = self._get_random_spinner(elapsed)
            
            # Add timer and message to the spinner
            spinner_with_text = Text()
            spinner_with_text.append(spinner)
            spinner_with_text.append(" ")
            spinner_with_text.append(f"{elapsed:.2f}s", style=f"bold {COLOR_PALETTE['text']}")
            spinner_with_text.append(f" - {message}")
            
            if with_philosophy:
                # For the philosophy quote
                quote_text = Text(quote, style=f"italic {COLOR_PALETTE['text']}")
                
                # Add an empty line for spacing
                spacer = Text("")
                
                # Group them together with proper spacing
                content = Group(quote_text, spacer, spinner_with_text)
            else:
                content = spinner_with_text
            
            panel = Panel(
                content,
                title=f"[bold {COLOR_PALETTE['text']}]⯁ Angela Initializing ⯁[/bold {COLOR_PALETTE['text']}]",
                border_style=COLOR_PALETTE["border"],  # Consistent red border 
                box=DEFAULT_BOX,
                padding=(1, 2)
            )
            
            return panel
        
        # Use try-except with asyncio.sleep to make it cancellable
        try:
            with Live(get_layout(), refresh_per_second=20, console=self._console, transient=True) as live:
                try:
                    while True:
                        await asyncio.sleep(0.03)  # Smaller sleep for smoother animation
                        live.update(get_layout())
                except asyncio.CancelledError:
                    # Handle cancellation gracefully
                    self._logger.debug("Loading display cancelled")
                    raise  # Re-raise to ensure proper cleanup
        except asyncio.CancelledError:
            # Expected when cancelled from outside
            pass
        except Exception as e:
            self._logger.error(f"Error displaying loading timer: {str(e)}")
    
    def _ensure_no_active_live(self):
        """Ensure no active Live displays by checking and resetting console state."""
        # Access the internal console state to check if it has an active Live
        if hasattr(self._console, "_live") and self._console._live:
            self._logger.warning("Detected active Live display. Attempting cleanup.")
            # Try to gracefully close any existing live display
            try:
                try:
                    # First try to stop it properly
                    self._console._live.stop()
                except Exception:
                    # If that fails, just set it to None
                    pass
                self._console._live = None
                # Reset other potentially problematic console state
                if hasattr(self._console, "_buffer"):
                    self._console._buffer = []
            except Exception as e:
                self._logger.error(f"Error cleaning up console state: {str(e)}")

    async def display_result_summary(self, result: Dict[str, Any]) -> None:
        """
        Display a summary of a command execution result without duplicating explanations.
        
        Args:
            result: The command execution result
        """
        # Extract data from the result
        command = result.get("command", "")
        stdout = result.get("stdout", "")
        stderr = result.get("stderr", "")
        success = result.get("success", False)
        
        # Only display output, not the command or explanations again
        if stdout.strip():
            self.print_output(stdout.strip(), OutputType.STDOUT)
        
        if stderr.strip():
            self.print_output(stderr.strip(), OutputType.STDERR)
        
        # Display overall status
        if success:
            if not stdout.strip() and not stderr.strip():
                # If no output, show a success message
                self._console.print("")
                self._console.print(f"[bold {COLOR_PALETTE['success']}]{ASCII_DECORATIONS['success']} Command executed successfully [/bold {COLOR_PALETTE['success']}]")
        else:
            if not stderr.strip():
                # If no error output but command failed
                self._console.print("")
                self._console.print(f"[bold {COLOR_PALETTE['error']}]{ASCII_DECORATIONS['error']} Command failed with exit code {result.get('return_code', 1)}[/bold {COLOR_PALETTE['error']}]")


    async def display_command_learning(
        self, 
        base_command: str, 
        count: int
    ) -> None:
        """
        Display a notification that a command has been used multiple times.
        
        Args:
            base_command: The command that was executed
            count: Number of times the command has been used
        """
        # Use a fancy learning prompt with purple styling (consistent with your palette)
        self._console.print(Panel(
            f"I noticed you've used [bold cyan]{base_command}[/bold cyan] {count} times.",
            title="Command Learning",
            border_style=COLOR_PALETTE["confirmation"],  # Purple border for consistency
            expand=False
        ))
    
    async def display_auto_execution_notice(
        self,
        command: str, 
        risk_level: int,
        preview: Optional[str],
        dry_run: bool = False
    ) -> None:
        """
        Show a notice for auto-execution with enhanced styling.
        
        Args:
            command: The command being auto-executed
            risk_level: Risk level of the command
            preview: Optional preview of what the command will do
        """
        # Risk styling
        risk_name = RISK_LEVEL_NAMES.get(risk_level, "UNKNOWN")
        risk_icon = RISK_ICONS.get(risk_level, "⚠")
        risk_color = RISK_COLORS.get(risk_level, COLOR_PALETTE["warning"])
        
        # Styled command with execution notice
        command_display = Group(
            Text(f"{risk_icon} Trusted Command ({risk_name} Risk)", style=COLOR_PALETTE["text"]),
            Text(""),  # Spacing
            Syntax(command, "bash", theme="vim", word_wrap=True)
        )
        
        self._console.print("\n")
        self._console.print(Panel(
            command_display,
            title=f"[bold {COLOR_PALETTE['text']}]◈ Auto-Executed Trusted Command ◈[/bold {COLOR_PALETTE['text']}]",
            border_style=COLOR_PALETTE["border"],
            box=DEFAULT_BOX,
            expand=False,
            padding=(1, 2)
        ))
        
        # Only show preview if it's enabled in preferences
        from angela.api.context import get_preferences_manager
        preferences_manager = get_preferences_manager()
        
        if preview and preferences_manager.preferences.ui.show_command_preview:
            self._console.print(Panel(
                Text(preview, style=COLOR_PALETTE["text"]),
                title=f"[bold {COLOR_PALETTE['text']}]❖ Command Preview ❖[/bold {COLOR_PALETTE['text']}]",
                border_style=COLOR_PALETTE["border"],
                box=DEFAULT_BOX,
                expand=False
            ))
        
        if not dry_run: 
            loading_task = asyncio.create_task(
                self.display_loading_timer("Auto-executing trusted command...", with_philosophy=True)
            )

            try:
                # Wait a minimum amount of time for visual feedback
                await asyncio.sleep(0.5)

                # Now we're ready to continue, cancel the loading task
                loading_task.cancel()
                try:
                    await loading_task
                except asyncio.CancelledError:
                    pass  # Expected
            except Exception as e:
                logger.error(f"Error managing loading display: {str(e)}")
                # Ensure the task is cancelled
                if not loading_task.done():
                    loading_task.cancel()
        
    
    async def display_command_preview(
        self,
        command: str, 
        preview: str
    ) -> None:
        """
        Display a command preview with consistent styling.
        
        Args:
            command: The command being previewed
            preview: Preview of what the command will do
        """
        self._console.print(Panel(
            preview,
            title=f"[bold {COLOR_PALETTE['text']}]⚡ Command Preview ⚡[/bold {COLOR_PALETTE['text']}]",
            border_style=COLOR_PALETTE["border"],  # Consistent red border
            box=DEFAULT_BOX,
            expand=False
        ))
    
    async def display_trust_added_message(
        self,
        command: str
    ) -> None:
        """
        Display a message when a command is added to trusted list.
        
        Args:
            command: The command that was trusted
        """
        base_command = command.split()[0] if command.split() else command
        self._console.print(f"Added [green]{base_command}[/green] to trusted commands.")

    async def display_command_summary(
        self,
        command: str,
        success: bool,
        stdout: str,
        stderr: str,
        return_code: int = 0,
        execution_time: Optional[float] = None
    ) -> None:
        """
        Display a comprehensive command execution summary.
        
        Args:
            command: The executed command
            success: Whether the command was successful
            stdout: Standard output from the command
            stderr: Standard error from the command
            return_code: Command return code
            execution_time: Execution time in seconds
        """
        # Command panel
        self.print_command(command, title="Command")
        
        # Output panel with styling
        if stdout.strip():
            # Create a styled panel for stdout
            stdout_panel = Panel(
                Text(stdout.strip(), style=COLOR_PALETTE["text"]),
                title=f"[bold {COLOR_PALETTE['success']}]{ASCII_DECORATIONS['output']} Output {ASCII_DECORATIONS['output']}[/bold {COLOR_PALETTE['success']}]",
                border_style=COLOR_PALETTE["border"],
                box=DEFAULT_BOX,
                expand=False,
                padding=(1, 2)
            )
            self._console.print("")
            self._console.print(stdout_panel)
        elif success:
            # Create a styled panel for success with no output
            success_panel = Panel(
                Text("Command executed successfully.", style=COLOR_PALETTE["success"]),
                title=f"[bold {COLOR_PALETTE['success']}]{ASCII_DECORATIONS['success']} Success {ASCII_DECORATIONS['success']}[/bold {COLOR_PALETTE['success']}]",
                border_style=COLOR_PALETTE["success"],
                box=DEFAULT_BOX,
                expand=False,
                padding=(1, 2)
            )
            self._console.print("")
            self._console.print(success_panel)
        
        # Error panel if command failed
        if not success:
            # Create a styled error panel
            if stderr.strip():
                error_panel = Panel(
                    Text(stderr.strip(), style=COLOR_PALETTE["error"]),
                    title=f"[bold {COLOR_PALETTE['error']}]{ASCII_DECORATIONS['error']} Error {ASCII_DECORATIONS['error']}[/bold {COLOR_PALETTE['error']}]",
                    border_style=COLOR_PALETTE["error"],
                    box=DEFAULT_BOX,
                    expand=False,
                    padding=(1, 2)
                )
                self._console.print("")
                self._console.print(error_panel)
            else:
                # Error with no stderr output
                error_panel = Panel(
                    Text(f"Command failed with exit code {return_code}", style=COLOR_PALETTE["error"]),
                    title=f"[bold {COLOR_PALETTE['error']}]{ASCII_DECORATIONS['error']} Error {ASCII_DECORATIONS['error']}[/bold {COLOR_PALETTE['error']}]",
                    border_style=COLOR_PALETTE["error"],
                    box=DEFAULT_BOX,
                    expand=False,
                    padding=(1, 2)
                )
                self._console.print("")
                self._console.print(error_panel)
        

# Global formatter instance
terminal_formatter = TerminalFormatter()
