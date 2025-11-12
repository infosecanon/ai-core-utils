# main.py
import logging
from pathlib import Path

# Import config (to check the env)
from core.config import settings
from core.diagram_renderer import render_plantuml_to_png

# Import core tools
from core.logging import setup_logging

# Import the tracer and renderer
from core.plantuml_tracer import global_tracer

# Read the config and set the log level
setup_logging(script_name="main_test_run")

# Get a logger instance
logger = logging.getLogger(__name__)

# Define some functions to trace
# We decorate them with the global tracer


@global_tracer.trace
def load_data(file_path: str) -> str:
    """A dummy function to simulate loading data."""
    logger.info(f"Loading data from: {file_path}")
    if file_path == "data.csv":
        return "some,csv,data"
    else:
        raise FileNotFoundError("File not found.")


@global_tracer.trace
def process_data(data: str) -> str:
    """A dummy function to simulate processing data."""
    logger.debug(f"Processing data: {data}")
    # Simulate a loop (3+ calls will be grouped by the tracer)
    for i in range(3):
        parse_row(f"row_{i}")
    return "processed_data"


@global_tracer.trace
def parse_row(row: str) -> bool:
    """A helper function to be called in a loop."""
    logger.debug(f"Parsing {row}")
    return True


@global_tracer.trace
def save_data(data: str, output_path: str) -> bool:
    """A dummy function to simulate saving data."""
    logger.info(f"Saving {data} to {output_path}")
    return True


def main() -> None:
    """Main execution logic."""
    logger.info(f"Starting main process in {settings.EDP_ENVIRONMENT} mode.")
    logger.debug("This is a DEBUG message. It will only show in 'Development' env.")
    logger.warning("This is a WARNING message.")

    # Run the traced code
    try:
        data = load_data("data.csv")
        processed = process_data(data)
        save_data(processed, "output.pkl")
    except FileNotFoundError as e:
        logger.error(f"A managed error occurred: {e}")

    try:
        # This call will fail and be traced
        load_data("other_file.csv")
    except Exception as e:
        logger.error(
            f"Second process failed as expected.\n \
                This is what an exception looks like: {e}",
            exc_info=True,
        )

    logger.info("Main process finished.")


if __name__ == "__main__":
    try:
        main()
    except Exception as e:
        logger.critical(f"Unhandled exception in main: {e}", exc_info=True)
    finally:
        # Generate the diagram at the very end
        logger.info("Generating trace diagram...")

        # Define where to save the diagram
        output_path = Path("reports/process_trace")

        # Get the diagram text from the singleton tracer
        puml_content = global_tracer.get_diagram()

        # Render the text to a .png file
        # This will create 'reports/process_trace.puml' and 'reports/process_trace.png'
        success = render_plantuml_to_png(puml_content, output_path)

        if success:
            logger.info(
                f"Successfully saved diagram to {output_path.with_suffix('.png')}"
            )
        else:
            logger.error("Failed to render trace diagram.")
