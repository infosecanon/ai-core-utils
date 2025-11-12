import logging
import subprocess
from pathlib import Path

# Get a logger for this module
logger = logging.getLogger(__name__)

# --- CONFIGURATION ---
# Default path to the plantuml.jar file.
# You can change this or pass it in the function call.
DEFAULT_PLANTUML_JAR = Path("src/core/plantuml-1.2025.10.jar")


def render_plantuml_to_png(
    puml_content: str,
    output_file_base: Path,
    plantuml_jar_path: Path = DEFAULT_PLANTUML_JAR,
) -> bool:
    """
    Renders a PlantUML string to a PNG file using the local .jar.

    This function will also create the source .puml file.

    Args:
        puml_content (str): The full PlantUML diagram string (including @startuml).
        output_file_base (Path): The base path for output,
                                e.g., Path("reports/my_trace").
                                This function will create "reports/my_trace.puml"
                                and "reports/my_trace.png".
        plantuml_jar_path (Path): Path to the plantuml.jar file.

    Returns:
        bool: True if rendering was successful, False otherwise.
    """
    puml_file = output_file_base.with_suffix(".puml")
    png_file = output_file_base.with_suffix(".png")

    try:
        # Ensure the output directory exists
        output_file_base.parent.mkdir(parents=True, exist_ok=True)

        # Save the .puml source file
        with open(puml_file, "w") as f:
            f.write(puml_content)
        logger.info(f"  ✓ Saved PlantUML source to {puml_file}")

        # Check for the .jar file
        if not plantuml_jar_path.exists():
            logger.error(f"  ❌ PlantUML .jar not found at: {plantuml_jar_path}")
            logger.error("  Please download it and place it in the correct path.")
            return False

        # Build and run the Java command
        command = [
            "java",
            "-jar",
            str(plantuml_jar_path),
            str(puml_file),  # The file to render
        ]

        result = subprocess.run(command, capture_output=True, text=True, check=True)

        if result.returncode == 0:
            if png_file.exists():
                logger.info(f"  ✓ Rendered PNG diagram to {png_file}")
                return True
            else:
                logger.error(
                    f"  ❌ Subprocess ran but PNG file not found at {png_file}."
                )
                logger.error(f"  STDOUT: {result.stdout}")
                logger.error(f"  STDERR: {result.stderr}")
                return False

    except FileNotFoundError:
        logger.error("  ❌ 'java' command not found.")
        logger.error("  Please ensure Java is installed and in your system's PATH.")
        return False
    except subprocess.CalledProcessError as e:
        logger.error(f"  ❌ PlantUML rendering failed (Return Code: {e.returncode}):")
        logger.error(f"  STDERR: {e.stderr}")
        return False
    except Exception as e:
        logger.error(
            f"  ❌ An unexpected error occurred during rendering: {e}", exc_info=True
        )
        return False

    return False
