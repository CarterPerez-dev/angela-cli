# angela/components/shell/formatter.py
"""
⚡ Enhanced terminal formatter for Angela CLI ⚡

This module provides an extraordinary terminal experience with
vibrant visuals, engaging animations, and stunning layout.
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

from angela.api.intent import get_advanced_task_plan_class, get_plan_step_type_enum
from angela.utils.logging import get_logger
from angela.constants import RISK_LEVELS

# ════════════════════════════════════════════════
# Custom box styles for incredible visual appeal
# ════════════════════════════════════════════════

NEBULA_BOX = box.Box("╭─╮││╰─╯")


COSMIC_BOX = box.Box("╭━╮┃┃╰━╯")


QUANTUM_BOX = box.Box("┏━┓┃┃┗━┛")


STELLAR_BOX = box.Box("╭═╮││╰═╯")

# ════════════════════════════════════════════════
# Stunning color palette that will blow minds
# ════════════════════════════════════════════════

COLOR_PALETTE = {
    "primary": "#ff0055",           # Vibrant red
    "secondary": "#8a2be2",         # Rich purple 
    "tertiary": "#00c8ff",          # Bright blue
    "accent1": "#00ffaa",           # Neon green
    "accent2": "#00ffff",           # Cyan
    "accent3": "#ffcc00",           # Yellow (used sparingly)
    "white": "#ffffff",             # Pure white (used minimally)
    "subtle": "#6c7280",            # Subdued color for less important elements
    "success": "#00ff99",           # Vibrant success green
    "warning": "#ffcc00",           # Warning yellow
    "danger": "#ff3355",            # Danger red
    "info": "#00c8ff",              # Information blue
    "background": "#100030",        # Deep background
    "purple_glow": "#c930ff",       # Purple with glow effect
    "text_primary": "#e0e0ff",      # Primary text color
    "text_secondary": "#c0c0dd",    # Secondary text color
    "command_bg": "#220033",        # Command background
    "command_border": "#ff0055",    # Command border
    "output_bg": "#001a33",         # Output background
    "output_border": "#00c8ff",     # Output border
    "safe": "#00ff99",              # Safe risk level
    "low": "#00c8ff",               # Low risk level
    "medium": "#ffcc00",            # Medium risk level
    "high": "#ff3355",              # High risk level
    "critical": "#ff0055",          # Critical risk level
}

# ════════════════════════════════════════════════
# Stunning ASCII artwork for visual impact
# ════════════════════════════════════════════════

ASCII_COMMAND = """
 ┏━━━━━━━━━━━━━━━━┓
 ┃  COMMAND PULSE ┃
 ┗━━━━━━━━━━━━━━━━┛
"""

ASCII_EXECUTION = """
 ▀▄▀▄▀▄ EXECUTING ▄▀▄▀▄▀
"""

ASCII_CONFIRMATION = """
 ┏━━━━━━━━━━━━━━━━━━━━━┓
 ┃ AWAITING DIRECTIVE  ┃
 ┗━━━━━━━━━━━━━━━━━━━━━┛
"""

ASCII_SUCCESS = """
 ┏━━━━━━━━━━━━━━━━━━━━━┓
 ┃  MISSION COMPLETE   ┃
 ┗━━━━━━━━━━━━━━━━━━━━━┛
"""

# ════════════════════════════════════════════════
# Risk level names and stunning visual styling
# ════════════════════════════════════════════════

RISK_LEVEL_NAMES = {v: k for k, v in RISK_LEVELS.items()}

# Visual styling for risk levels with mind-blowing effects
RISK_COLORS = {
    RISK_LEVELS["SAFE"]: COLOR_PALETTE["safe"],
    RISK_LEVELS["LOW"]: COLOR_PALETTE["low"],
    RISK_LEVELS["MEDIUM"]: COLOR_PALETTE["medium"],
    RISK_LEVELS["HIGH"]: COLOR_PALETTE["high"],
    RISK_LEVELS["CRITICAL"]: COLOR_PALETTE["critical"],
}

RISK_ICONS = {
    RISK_LEVELS["SAFE"]: "✓ ",
    RISK_LEVELS["LOW"]: "⚡ ",
    RISK_LEVELS["MEDIUM"]: "⚠ ",
    RISK_LEVELS["HIGH"]: "❗ ",
    RISK_LEVELS["CRITICAL"]: "⛔ ",
}

RISK_BOX_STYLES = {
    RISK_LEVELS["SAFE"]: NEBULA_BOX,
    RISK_LEVELS["LOW"]: NEBULA_BOX,
    RISK_LEVELS["MEDIUM"]: COSMIC_BOX,
    RISK_LEVELS["HIGH"]: QUANTUM_BOX,
    RISK_LEVELS["CRITICAL"]: STELLAR_BOX,
}

AdvancedTaskPlan = get_advanced_task_plan_class()
PlanStepType = get_plan_step_type_enum()

_console = Console(record=True, width=100)

logger = get_logger(__name__)

class OutputType(Enum):
    """Types of command output with enhanced visual identity."""
    STDOUT = "stdout"
    STDERR = "stderr"
    INFO = "info"
    SUCCESS = "success"
    WARNING = "warning"
    ERROR = "error"
    PROGRESS = "progress"

class TerminalFormatter:
    """
    Enhanced terminal formatter with stunning visual effects,
    mind-blowing animations, and extraordinary user experience.
    """

    # Replace fun loading quotes with philosophical wisdom
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
        """Initialize the terminal formatter with stunning capabilities."""
        self._console = Console()
        self._logger = logger
        self._active_displays = set()
        
        # Additional properties for enhanced visual effects
        self._current_animation_frame = 0
        self._animation_frames = self._generate_animation_frames()
        
    def _generate_animation_frames(self) -> List[str]:
        """Generate stunning animation frames for visual effects."""
        return [
            "◈ ◇ ◇ ◇ ◇",
            "◇ ◈ ◇ ◇ ◇",
            "◇ ◇ ◈ ◇ ◇",
            "◇ ◇ ◇ ◈ ◇",
            "◇ ◇ ◇ ◇ ◈",
            "◇ ◇ ◇ ◈ ◇",
            "◇ ◇ ◈ ◇ ◇",
            "◇ ◈ ◇ ◇ ◇"
        ]

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
        spinner_text.append(trail, style=COLOR_PALETTE["tertiary"])
        
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
            spinner_text.append(flame_chars[flame_idx], style=COLOR_PALETTE["primary"])
            spinner_text.append("~", style=COLOR_PALETTE["accent3"])
            
        elif element_cycle == 1:  # Water
            water_symbols = ["≈", "≋", "≈", "∽", "∿", "≈"]
            water_idx = int(elapsed * 12) % len(water_symbols)
            
            # Wave effect
            wave_level = int(2 + 2 * math.sin(elapsed * 6))
            waves = "~" * wave_level
            
            spinner_text.append(water_symbols[water_idx], style=COLOR_PALETTE["tertiary"])
            spinner_text.append(waves, style=COLOR_PALETTE["accent2"])
            spinner_text.append("○", style=COLOR_PALETTE["tertiary"])
            
        elif element_cycle == 2:  # Earth
            earth_symbols = ["◦", "•", "●", "◎", "◉", "⦿", "◉", "◎", "●", "•"]
            earth_idx = int(elapsed * 10) % len(earth_symbols)
            
            # Growth effect
            growth = [".", "․", "‥", "…", "⁘", "⁙"]
            growth_idx = int(elapsed * 6) % len(growth)
            
            spinner_text.append(earth_symbols[earth_idx], style=COLOR_PALETTE["accent1"])
            spinner_text.append(growth[growth_idx], style=COLOR_PALETTE["accent1"])
            spinner_text.append("⏣", style=COLOR_PALETTE["accent1"])
            
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
            spinner_text.append("◌", style=COLOR_PALETTE["accent2"])
        
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
        spinner_text.append("=", style=COLOR_PALETTE["tertiary"])
        spinner_text.append(core_char * energy_level, style=COLOR_PALETTE["accent3"])
        spinner_text.append("=", style=COLOR_PALETTE["tertiary"])
        
        # Starfield effect - stars zooming past at different speeds
        star_positions = []
        for i in range(5):  # Generate 5 stars
            # Each star moves at different speeds
            pos = (elapsed * (5 + i)) % 15
            intensity = min(1.0, 15 - pos) / 1.0  # Fade based on position
            
            if intensity > 0.7:
                style = COLOR_PALETTE["white"]
            elif intensity > 0.4:
                style = COLOR_PALETTE["text_primary"]
            else:
                style = COLOR_PALETTE["text_secondary"]
                
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
            spinner_text.append("⚡", style=COLOR_PALETTE["accent2"])
        elif fluctuation == 1:
            spinner_text.append("⚡", style=COLOR_PALETTE["secondary"])
        else:
            spinner_text.append("⚡", style=COLOR_PALETTE["accent3"])
        
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

    def print_command(self, command: str, title: Optional[str] = None, risk_level: int = 0) -> None:
        """
        Display a command with extraordinary styling and visual effects.
        
        Args:
            command: The command to display
            title: Optional title for the panel
            risk_level: Risk level for styling (0-4)
        """
        # Get risk styling
        risk_color = RISK_COLORS.get(risk_level, COLOR_PALETTE["primary"])
        risk_box = RISK_BOX_STYLES.get(risk_level, NEBULA_BOX)
        
        # Create title with enhanced styling if provided
        panel_title = f"[bold {risk_color}]⚡ {title or 'Command Pulse'} ⚡[/bold {risk_color}]"
        
        # Create extraordinary styled command display
        syntax = Syntax(command, "bash", theme="monokai", word_wrap=True, background_color=COLOR_PALETTE["command_bg"])
        
        # Create visually stunning panel
        panel = Panel(
            syntax,
            title=panel_title,
            border_style=risk_color,
            box=risk_box,
            expand=False,
            padding=(1, 2)
        )
        
        # Add visual separator and display
        self._console.print("")
        self._console.print(panel)
    
    def print_output(
        self, 
        output: str, 
        output_type: OutputType = OutputType.STDOUT,
        title: Optional[str] = None
    ) -> None:
        """
        Display command output with mind-blowing styling and visual effects.
        
        Args:
            output: The output text
            output_type: Type of output
            title: Optional title for the panel
        """
        if not output:
            return
            
        # Set styling based on output type with enhanced visual appeal
        if output_type == OutputType.STDERR or output_type == OutputType.ERROR:
            style = COLOR_PALETTE["danger"]
            title = title or "⚠ Error Output ⚠"
            border_style = style
            box_style = QUANTUM_BOX
        elif output_type == OutputType.WARNING:
            style = COLOR_PALETTE["warning"]
            title = title or "⚠ Warning ⚠"
            border_style = style
            box_style = COSMIC_BOX
        elif output_type == OutputType.SUCCESS:
            style = COLOR_PALETTE["success"]
            title = title or "✓ Success ✓"
            border_style = style
            box_style = NEBULA_BOX
        elif output_type == OutputType.INFO:
            style = COLOR_PALETTE["info"]
            title = title or "ℹ Information ℹ"
            border_style = style
            box_style = NEBULA_BOX
        else:  # Default for STDOUT with enhanced styling
            style = COLOR_PALETTE["tertiary"]
            title = title or "◈ Command Output ◈"
            border_style = style
            box_style = NEBULA_BOX
        
        # Create visually stunning panel
        panel = Panel(
            output,
            title=f"[bold {style}]{title}[/bold {style}]",
            border_style=border_style,
            box=box_style,
            expand=False,
            padding=(1, 2)
        )
        
        # Add visual separator and display
        self._console.print("")
        self._console.print(panel)

    def print_success_message(self, message: str, title: str = "Operation Complete") -> None:
        """
        Display a success message with stunning visual effects.
        
        Args:
            message: The success message
            title: The panel title
        """
        # Create a visually appealing success panel
        panel = Panel(
            f"[{COLOR_PALETTE['success']}]{message}[/{COLOR_PALETTE['success']}]",
            title=f"[bold {COLOR_PALETTE['success']}]✓ {title} ✓[/bold {COLOR_PALETTE['success']}]",
            border_style=COLOR_PALETTE["success"],
            box=NEBULA_BOX,
            expand=False,
            padding=(1, 2)
        )
        
        # Add visual separator and display
        self._console.print("")
        self._console.print(panel)
    
    def print_error_analysis(self, analysis: Dict[str, Any]) -> None:
        """
        Display error analysis with extraordinary visual styling and helpful insights.
        
        Args:
            analysis: The error analysis dictionary
        """
        # Create a visually striking table for error analysis
        table = Table(
            title=f"[bold {COLOR_PALETTE['danger']}]⚠ Error Analysis ⚠[/bold {COLOR_PALETTE['danger']}]",
            border_style=COLOR_PALETTE["danger"],
            box=QUANTUM_BOX,
            highlight=True,
            expand=False,
            show_lines=True
        )
        
        # Add columns with enhanced styling
        table.add_column(f"[{COLOR_PALETTE['secondary']}]Aspect[/{COLOR_PALETTE['secondary']}]", style=f"{COLOR_PALETTE['secondary']}", justify="right")
        table.add_column(f"[{COLOR_PALETTE['text_primary']}]Details[/{COLOR_PALETTE['text_primary']}]", style=f"{COLOR_PALETTE['text_primary']}")
        
        # Add error summary with striking styling
        table.add_row(
            "Error", 
            Text(analysis.get("error_summary", "Unknown error"), style=COLOR_PALETTE["danger"])
        )
        
        # Add possible cause with enhanced visual cues
        table.add_row(
            "Possible Cause", 
            Text(analysis.get("possible_cause", "Unknown"), style=COLOR_PALETTE["text_primary"])
        )
        
        # Add command issues with improved visual hierarchy
        if analysis.get("command_issues"):
            issues = "\n".join(f"• {issue}" for issue in analysis["command_issues"])
            table.add_row("Command Issues", Text(issues, style=COLOR_PALETTE["text_primary"]))
        
        # Add file issues with enhanced visual cues
        if analysis.get("file_issues"):
            file_issues = []
            for issue in analysis["file_issues"]:
                path = issue.get("path", "unknown")
                if "suggestion" in issue:
                    file_issues.append(f"• [{COLOR_PALETTE['danger']}]{path}[/{COLOR_PALETTE['danger']}]: {issue['suggestion']}")
                if "similar_files" in issue:
                    similar = ", ".join(f"[{COLOR_PALETTE['tertiary']}]{f}[/{COLOR_PALETTE['tertiary']}]" for f in issue["similar_files"])
                    file_issues.append(f"  Did you mean: {similar}?")
            
            if file_issues:
                table.add_row("File Issues", Text.from_markup("\n".join(file_issues)))
        
        # Display the table with visual separator
        self._console.print("")
        self._console.print(table)
        
        # Display fix suggestions if available with stunning styling
        if analysis.get("fix_suggestions"):
            suggestions = analysis["fix_suggestions"]
            if suggestions:
                suggestion_items = "\n".join(f"[bold {COLOR_PALETTE['accent1']}]→[/bold {COLOR_PALETTE['accent1']}] {suggestion}" for suggestion in suggestions)
                
                # Create visually appealing suggestion panel
                self._console.print(Panel(
                    Text.from_markup(suggestion_items),
                    title=f"[bold {COLOR_PALETTE['accent1']}]✨ Fix Suggestions ✨[/bold {COLOR_PALETTE['accent1']}]",
                    border_style=COLOR_PALETTE["accent1"],
                    box=NEBULA_BOX,
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
        Display a comprehensive pre-confirmation information block with extraordinary styling.
        
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
        # Get console width to ensure proper text wrapping
        console_width = self._console.width
        max_text_width = min(console_width - 10, 80)  # Leave some margin
        
        # Risk level styling with enhanced visual cues
        risk_name = RISK_LEVEL_NAMES.get(risk_level, "UNKNOWN")
        risk_color = RISK_COLORS.get(risk_level, COLOR_PALETTE["warning"])
        risk_icon = RISK_ICONS.get(risk_level, "⚠ ")
        risk_box = RISK_BOX_STYLES.get(risk_level, NEBULA_BOX)
        
        # Create a stunning layout for all information
        layout = Layout()
        
        # Split into top and bottom sections
        layout.split(
            Layout(name="top", ratio=3),
            Layout(name="bottom", ratio=2)
        )
        
        # Split top into command and explanation
        layout["top"].split_row(
            Layout(name="command", ratio=2),
            Layout(name="explanation", ratio=3)
        )
        
        # Split bottom into confidence, risk, and preview
        layout["bottom"].split_row(
            Layout(name="confidence", ratio=1),
            Layout(name="risk", ratio=1),
            Layout(name="preview", ratio=2)
        )
        
        # 1. Command panel with stunning styling specific to risk level
        title = f"[bold {risk_color}]{risk_icon}Execute [{risk_name} Risk][/bold {risk_color}]"
        syntax = Syntax(command, "bash", theme="monokai", word_wrap=True, background_color=COLOR_PALETTE["command_bg"])
        command_panel = Panel(
            syntax,
            title=title,
            border_style=risk_color,
            box=risk_box,
            expand=True,
            padding=(1, 2)
        )
        layout["command"].update(command_panel)
        
        # 2. Explanation panel with enhanced styling
        if explanation:
            # Ensure explanation doesn't get cut off
            wrapped_explanation = textwrap.fill(explanation, width=max_text_width)
            
            explanation_panel = Panel(
                Text(wrapped_explanation, style=COLOR_PALETTE["text_primary"]),
                title=f"[bold {COLOR_PALETTE['secondary']}]✧ Command Insight ✧[/bold {COLOR_PALETTE['secondary']}]",
                border_style=COLOR_PALETTE["secondary"],
                box=NEBULA_BOX,
                expand=True,
                padding=(1, 2)
            )
            layout["explanation"].update(explanation_panel)
        else:
            layout["explanation"].update(Panel(
                "",
                title="[dim]No explanation available[/dim]",
                border_style="dim",
                expand=True
            ))
        
        # 3. Confidence score with extraordinary visual representation
        if confidence_score is not None:
            confidence_color = COLOR_PALETTE["success"] if confidence_score > 0.8 else COLOR_PALETTE["tertiary"] if confidence_score > 0.6 else COLOR_PALETTE["danger"]
            confidence_stars = int(confidence_score * 5)
            confidence_display = "★" * confidence_stars + "☆" * (5 - confidence_stars)
            
            confidence_panel = Panel(
                Group(
                    Text(f"Score: [{confidence_color}]{confidence_score:.2f}[/{confidence_color}]", justify="center"),
                    Text(confidence_display, style=confidence_color, justify="center"),
                    Text("", justify="center"),
                    Text("(AI confidence in command accuracy)", style="dim", justify="center")
                ),
                title=f"[bold {COLOR_PALETTE['tertiary']}]✧ AI Confidence ✧[/bold {COLOR_PALETTE['tertiary']}]",
                border_style=confidence_color,
                box=NEBULA_BOX,
                expand=True,
                padding=(1, 1)
            )
            layout["confidence"].update(confidence_panel)
        else:
            layout["confidence"].update(Panel(
                "",
                title="[dim]No confidence data[/dim]",
                border_style="dim",
                expand=True
            ))
        
        # 4. Risk assessment panel with enhanced visual effects
        risk_impact = self._format_impact_analysis(impact)
        risk_info = Group(
            Text(f"{risk_icon}Level: [{risk_color}]{risk_name}[/{risk_color}]", justify="center"),
            Text("", justify="center"),
            Text(f"Reason: {risk_reason}", style=COLOR_PALETTE["text_primary"], justify="center"),
        )
        
        risk_panel = Panel(
            risk_info,
            title=f"[bold {risk_color}]⚠ Risk Assessment ⚠[/bold {risk_color}]",
            border_style=risk_color,
            box=risk_box,
            expand=True,
            padding=(1, 1)
        )
        layout["risk"].update(risk_panel)
        
        # 5. Preview panel with stunning styling
        if preview:
            # Ensure preview is properly formatted
            preview_panel = Panel(
                Text(preview, style=COLOR_PALETTE["text_primary"]),
                title=f"[bold {COLOR_PALETTE['tertiary']}]⚡ Command Preview ⚡[/bold {COLOR_PALETTE['tertiary']}]",
                border_style=COLOR_PALETTE["tertiary"],
                box=NEBULA_BOX,
                expand=True,
                padding=(1, 2)
            )
            layout["preview"].update(preview_panel)
        else:
            # Provide a visually appealing message for dry run
            layout["preview"].update(Panel(
                Text("Preview not available for this command. Use --dry-run for simulation.", style=COLOR_PALETTE["text_secondary"]),
                title=f"[{COLOR_PALETTE['tertiary']}]⚠ Preview Unavailable ⚠[/{COLOR_PALETTE['tertiary']}]",
                border_style=COLOR_PALETTE["tertiary"],
                box=NEBULA_BOX,
                expand=True,
                padding=(1, 2)
            ))
        
        # 6. Warning for critical operations
        if risk_level >= 4:  # CRITICAL
            critical_warning = Panel(
                Text(f"⚠️  This is a CRITICAL risk operation  ⚠️\nIt may cause significant changes to your system or data loss.", style=COLOR_PALETTE["danger"]),
                title=f"[bold {COLOR_PALETTE['danger']}]⚠ CRITICAL RISK WARNING ⚠[/bold {COLOR_PALETTE['danger']}]",
                border_style=COLOR_PALETTE["danger"],
                box=STELLAR_BOX,
                expand=False,
                padding=(1, 2)
            )
            self._console.print(critical_warning)
        
        # Print the complete layout
        self._console.print(layout)

    def _format_impact_analysis(self, impact: Dict[str, Any]) -> Text:
        """
        Format the command impact analysis into a visually stunning text.
        
        Args:
            impact: The impact analysis dictionary
            
        Returns:
            A rich Text object with the formatted impact analysis
        """
        text = Text()
        
        # Add operation types with enhanced styling
        operations = impact.get("operations", ["unknown"])
        text.append("Operations: ", style=f"bold {COLOR_PALETTE['secondary']}")
        text.append(", ".join(operations), style=COLOR_PALETTE["text_primary"])
        text.append("\n")
        
        # Add destructive warning if applicable with enhanced visual cues
        if impact.get("destructive", False):
            text.append("⚠️ Warning: ", style=f"bold {COLOR_PALETTE['danger']}")
            text.append("This operation may delete or overwrite files", style=COLOR_PALETTE["danger"])
            text.append("\n")
        
        # Add file creation info with visually appealing styling
        if impact.get("creates_files", False):
            text.append("Creates Files: ", style=f"bold {COLOR_PALETTE['accent1']}")
            text.append("Yes", style=COLOR_PALETTE["accent1"])
            text.append("\n")
        
        # Add file modification info with stunning visual representation
        if impact.get("modifies_files", False):
            text.append("Modifies Files: ", style=f"bold {COLOR_PALETTE['tertiary']}")
            text.append("Yes", style=COLOR_PALETTE["tertiary"])
            text.append("\n")
        
        return text

    async def display_inline_confirmation(
        self,
        prompt_text: str = "Proceed with execution?"
    ) -> bool:
        """
        Display an extraordinary inline confirmation prompt with stunning visual effects.
        
        Args:
            prompt_text: The confirmation prompt text
            
        Returns:
            True if confirmed, False otherwise
        """
        # Create an eye-catching confirmation prompt
        from rich import box
        
        # Extract risk level from prompt if present
        risk_style = COLOR_PALETTE["tertiary"]  # Default color
        
        # Check for risk levels in the prompt text
        if "SAFE" in prompt_text:
            risk_style = COLOR_PALETTE["safe"]
            box_type = NEBULA_BOX
        elif "LOW" in prompt_text:
            risk_style = COLOR_PALETTE["low"]
            box_type = NEBULA_BOX
        elif "MEDIUM" in prompt_text:
            risk_style = COLOR_PALETTE["medium"]
            box_type = COSMIC_BOX
        elif "HIGH" in prompt_text:
            risk_style = COLOR_PALETTE["high"]
            box_type = QUANTUM_BOX
        elif "CRITICAL" in prompt_text:
            risk_style = COLOR_PALETTE["critical"]
            box_type = STELLAR_BOX
        else:
            box_type = NEBULA_BOX
        
        # Create a visually stunning confirmation prompt
        panel_group = Group(
            Text(prompt_text, style=COLOR_PALETTE["text_primary"], justify="center"),
            Text("", justify="center"),  # Empty line for spacing
            Text.from_markup(f"([bold {COLOR_PALETTE['success']}]y[/bold {COLOR_PALETTE['success']}]/[bold {COLOR_PALETTE['danger']}]n[/bold {COLOR_PALETTE['danger']}])", justify="center")
        )
        
        confirmation_panel = Panel(
            panel_group,
            title=f"[bold {risk_style}]◈ Awaiting Confirmation ◈[/bold {risk_style}]",
            border_style=risk_style,
            box=box_type,
            expand=False,
            padding=(1, 4)
        )
        
        self._console.print("")  # Add spacing
        self._console.print(confirmation_panel)
        
        # Create stunning prompt indicator
        self._console.print(Text(f"[bold {risk_style}]>>> [/bold {risk_style}]", end=""))
        
        # Get user input
        response = input().strip().lower()
        
        # Consider empty response or y/yes as "yes"
        if not response or response in ("y", "yes"):
            return True
        
        # Everything else is "no"
        return False

    async def display_execution_timer(
        self,
        command: str,
        with_philosophy: bool = True
    ) -> Tuple[str, str, int, float]:
        """
        Display a command execution timer with stunning visual effects and philosophy quotes.
        
        Args:
            command: The command being executed
            with_philosophy: Whether to display philosophy quotes
            
        Returns:
            Tuple of (stdout, stderr, return_code, execution_time)
        """
        import random
        import time
        import math  # For advanced effects
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
        
        start_time = time.time()
        
        # Choose a random philosophy quote
        quote = random.choice(self.PHILOSOPHY_QUOTES) if with_philosophy else ""
        
        # Create a layout for execution display
        def get_layout():
            elapsed = time.time() - start_time
            
            # Get a random but consistent spinner for this execution session
            spinner = self._get_random_spinner(elapsed)
            
            # Add execution message with enhanced styling
            spinner_with_text = Text()
            spinner_with_text.append(spinner)
            spinner_with_text.append(" ")
            spinner_with_text.append(f"{elapsed:.2f}s", style=f"bold {COLOR_PALETTE['accent1']}")
            spinner_with_text.append(" - ", style=COLOR_PALETTE["text_secondary"])
            spinner_with_text.append("Executing command...", style=COLOR_PALETTE["tertiary"])
            
            if with_philosophy:
                # For the philosophy quote with stunning styling
                quote_text = Text(quote, style=f"italic {COLOR_PALETTE['secondary']}")
                
                # Add an empty line for spacing
                spacer = Text("")
                
                # Group them together with proper spacing
                content = Group(quote_text, spacer, spinner_with_text)
            else:
                content = spinner_with_text
            
            # Create a visually striking panel
            panel = Panel(
                content,
                title=f"[bold {COLOR_PALETTE['tertiary']}]◈ Command Execution ◈[/bold {COLOR_PALETTE['tertiary']}]",
                border_style=COLOR_PALETTE["tertiary"],
                box=NEBULA_BOX,
                padding=(1, 2)
            )
            
            return panel
        
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
                completed_panel = Panel(
                    Text(f"Execution completed in {execution_time:.6f}s", style=COLOR_PALETTE["success"], justify="center"),
                    title=f"[bold {COLOR_PALETTE['success']}]✓ Angela Initialized ✓[/bold {COLOR_PALETTE['success']}]",
                    border_style=COLOR_PALETTE["success"],
                    box=NEBULA_BOX,
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
        Display a loading timer with stunning visual effects and philosophy quotes.
        
        Args:
            message: The loading message to display
            with_philosophy: Whether to display philosophy quotes
        """
        import random
        import time
        import math  
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
            
            # Add timer and message to the spinner with enhanced styling
            spinner_with_text = Text()
            spinner_with_text.append(spinner)
            spinner_with_text.append(" ")
            spinner_with_text.append(f"{elapsed:.2f}s", style=f"bold {COLOR_PALETTE['accent1']}")
            spinner_with_text.append(f" - {message}", style=COLOR_PALETTE["tertiary"])
            
            if with_philosophy:
                # For the philosophy quote with stunning styling
                quote_text = Text(quote, style=f"italic {COLOR_PALETTE['secondary']}")
                
                # Add an empty line for spacing
                spacer = Text("")
                
                # Group them together with proper spacing
                content = Group(quote_text, spacer, spinner_with_text)
            else:
                content = spinner_with_text
            
            # Create a visually striking panel
            panel = Panel(
                content,
                title=f"[bold {COLOR_PALETTE['tertiary']}]◈ Angela initializing... ◈[/bold {COLOR_PALETTE['tertiary']}]",
                border_style=COLOR_PALETTE["tertiary"],
                box=NEBULA_BOX,
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

    def print_command_learning(self, command_type: str, count: int) -> None:
        """
        Display command learning notification with extraordinary styling.
        
        Args:
            command_type: Type of command that's being learned
            count: Number of times this command has been used
        """
        # Create a visually stunning panel for command learning
        panel = Panel(
            Text(f"I noticed you've used {command_type} {count} times.", style=COLOR_PALETTE["tertiary"]),
            title=f"[bold {COLOR_PALETTE['secondary']}]✧ Command Learning ✧[/bold {COLOR_PALETTE['secondary']}]",
            border_style=COLOR_PALETTE["secondary"],
            box=COSMIC_BOX,
            expand=False,
            padding=(1, 2)
        )
        
        # Add visual separator and display
        self._console.print("")
        self._console.print(panel)
    
    def print_command_added(self, command_type: str) -> None:
        """
        Display notification that a command was added to trusted commands with stunning styling.
        
        Args:
            command_type: Type of command that was added
        """
        # Create a visually striking success message
        self.print_success_message(
            f"Command '{command_type}' has been added to your trusted commands list.",
            "Auto-Execution Enabled"
        )
    
    def print_command_output_result(self, stdout: str, stderr: str, return_code: int) -> None:
        """
        Display command execution results with extraordinary styling.
        
        Args:
            stdout: Standard output from command
            stderr: Standard error from command
            return_code: Return code from command
        """
        # Check if command was successful
        if return_code == 0:
            # Command succeeded
            if stdout.strip():
                # Show output with stunning styling
                self.print_output(
                    stdout,
                    OutputType.STDOUT,
                    "⚡ Command Output ⚡"
                )
            else:
                # Show success message for commands with no output
                self.print_success_message(
                    "Command executed successfully with no visible output.",
                    "Command Complete"
                )
        else:
            # Command failed, show error
            if stderr.strip():
                self.print_output(
                    stderr,
                    OutputType.STDERR,
                    "⚠ Command Error ⚠"
                )
            else:
                # Generic error message if no stderr
                self.print_output(
                    f"Command failed with return code {return_code}",
                    OutputType.ERROR,
                    "⚠ Execution Failed ⚠"
                )

    def print_adaptive_confirmation(self, prompt_text: str) -> None:
        """
        Display a request for adaptive confirmation with extraordinary styling.
        
        Args:
            prompt_text: The confirmation prompt text
        """
        # Create a visually striking panel for adaptive confirmation
        panel = Panel(
            Text(prompt_text, style=COLOR_PALETTE["text_primary"], justify="center"),
            title=f"[bold {COLOR_PALETTE['secondary']}]✧ Adaptive Learning ✧[/bold {COLOR_PALETTE['secondary']}]",
            border_style=COLOR_PALETTE["secondary"],
            box=COSMIC_BOX,
            expand=False,
            padding=(1, 2)
        )
        
        # Add visual separator and display
        self._console.print("")
        self._console.print(panel)
    
    # Additional helper methods for visual enhancements
    def create_table(self, title: str, columns: List[Tuple[str, str]], box_style=NEBULA_BOX) -> Table:
        """Create a visually stunning table."""
        table = Table(
            title=f"[bold {COLOR_PALETTE['tertiary']}]{title}[/bold {COLOR_PALETTE['tertiary']}]",
            box=box_style,
            border_style=COLOR_PALETTE["tertiary"],
            highlight=True,
            expand=False
        )
        
        for name, style in columns:
            table.add_column(f"[{style}]{name}[/{style}]", style=style)
            
        return table
    
    def create_success_indicator(self, success: bool, text: str = "") -> Text:
        """Create a visually stunning success/failure indicator."""
        if success:
            return Text(f"✓ {text}", style=COLOR_PALETTE["success"])
        else:
            return Text(f"✗ {text}", style=COLOR_PALETTE["danger"])

# Global formatter instance
terminal_formatter = TerminalFormatter()
