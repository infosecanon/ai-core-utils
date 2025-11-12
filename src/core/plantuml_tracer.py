import functools
import inspect

# Get a logger for this module, assuming logging is set up elsewhere
import logging
import sys
from pathlib import Path
from typing import Any, Callable, Optional, ParamSpec, TypeVar

import pandas as pd

# Create a ParamSpec to capture the arguments
P = ParamSpec("P")

# Create a TypeVar to capture the return type
R = TypeVar("R")

logger = logging.getLogger(__name__)


class PlantUMLTracer:
    """
    Generates a PlantUML sequence diagram string from decorated function calls.

    This class is intended to be used as a singleton via the
    'global_tracer' instance exported by this module.

    Usage:
    tracer = PlantUMLTracer()

    @tracer.trace
    def my_func(a, b):
        # ...
        pass

    # Run your code
    my_func(1, 2)

    # Get the diagram
    print(tracer.get_diagram())
    """

    # How many repeated calls before we collapse them into a loop?
    # 3 means 1 or 2 calls will be unrolled, 3+ will be a loop.
    LOOP_THRESHOLD = 3

    def __init__(self) -> None:
        # Use a list to build the string
        self._uml_lines = ["@startuml"]
        self._participants: set[str] = set()

        # This will store the data for the call we are
        # "holding" to check for repeats.
        self._pending_call: Optional[dict[str, Any]] = None
        # Format: {
        #   'info': (caller_name, callee_name),
        #   'lines': [list of log lines for one call],
        #   'count': 1
        # }

    def _add_participant(self, name: Any) -> None:
        """Register a participant (actor) in the diagram if new."""

        if name not in self._participants:
            self._participants.add(name)
            # Insert participant declaration after @startuml
            self._uml_lines.insert(1, f'participant "{name}"')

    def _format_value(self, val: Any) -> Any:
        """
        Intelligently formats values for the diagram.
        This version is robust against complex objects.
        """

        try:
            # Handle None
            if val is None:
                return "None"

            # Handle Class objects (e.g., XGBoostModel)
            if inspect.isclass(val):
                return f"<Class: {val.__name__}>"

            # Handle pandas objects
            if "pandas" in sys.modules:
                if isinstance(val, pd.DataFrame):
                    return f"<DataFrame shape={val.shape}>"
                if isinstance(val, pd.Series):
                    name = val.name if val.name else "Series"
                    return f"<{name} len={len(val)}>"

            # Simple types
            if isinstance(val, (str, int, float, bool)):
                return repr(val)

            # Handle Path objects
            if isinstance(val, Path):
                return f"Path('{val.name}')"

            # For lists, dicts, tuples - DO NOT repr the contents,
            # as they may contain unformattable objects.
            if isinstance(val, (list, dict, tuple)):
                return f"<{type(val).__name__} len={len(val)}>"

            # For all other instantiated objects
            return f"<{type(val).__name__} object>"

        except Exception:
            # Final fallback for any unknown error
            try:
                return f"<Object type: {type(val).__name__}>"
            except Exception:
                return "<Error: Unformattable Object>"

    def _flush_pending_call(self) -> None:
        """
        Writes the "held" call (and its repeats) to the log.
        This is called when a new, different call comes in, or at the end.
        """
        if not self._pending_call:
            return

        call_data = self._pending_call

        if call_data["count"] >= self.LOOP_THRESHOLD:
            # We have a loop! Write the loop block
            logger.info(
                f"Collapsing {call_data['count']} calls \
                    to {call_data['info'][1]} into loop."
            )
            self._uml_lines.append(f"loop {call_data['count']} times")
            self._uml_lines.extend(call_data["lines"])
            self._uml_lines.append("end")
        else:
            # Not enough repeats, just unroll the calls
            for _ in range(call_data["count"]):
                self._uml_lines.extend(call_data["lines"])

        # Clear the pending call
        self._pending_call = None

    def trace(self, func: Callable[P, R]) -> Callable[P, R]:
        """A decorator to trace function entry and exit, with loop detection."""

        @functools.wraps(func)
        def wrapper(*args: P.args, **kwargs: P.kwargs) -> Any:
            # Get Caller and Callee
            callee_name = func.__name__
            caller_name = "Unknown"
            try:
                caller_frame = inspect.stack()[1]
                caller_name = caller_frame.function
                if caller_name == "<module>":
                    module_path = caller_frame.filename
                    module_name = Path(module_path).name
                    caller_name = f"[Module: {module_name}]"
            except IndexError:
                caller_name = "User"
            except Exception:
                pass

            self._add_participant(caller_name)
            self._add_participant(callee_name)

            # Format Call Signature & Check for Loop
            args_repr = [self._format_value(a) for a in args]
            kwargs_repr = [f"{k}={self._format_value(v)}" for k, v in kwargs.items()]
            # Shorten signature if it's too long
            full_sig = f"{', '.join(args_repr + kwargs_repr)}"
            if len(full_sig) > 100:
                full_sig = f"{full_sig[:100]}..."
            call_signature = f"{callee_name}({full_sig})"

            current_call_info = (caller_name, callee_name)

            # Check for Loop
            if self._pending_call and self._pending_call["info"] == current_call_info:
                # --- This is a repeat! ---
                # 1. Increment counter.
                self._pending_call["count"] += 1

                # 2. Execute the function but DO NOT log anything.
                try:
                    result = func(*args, **kwargs)
                    return result
                except Exception:
                    raise  # Re-raise

            else:
                # This is a new call
                # Flush the *previous* call (if any)
                self._flush_pending_call()

                # Build the call lines for THIS call
                call_lines = [
                    f'"{caller_name}" -> "{callee_name}": {call_signature}',
                    f'activate "{callee_name}"',
                ]

                # Execute and get return/exception lines
                return_lines = []
                exception_to_raise = None

                try:
                    result = func(*args, **kwargs)
                    formatted_result = self._format_value(result)
                    return_lines.append(
                        f'"{callee_name}" --> "{caller_name}": \
                            return {formatted_result}'
                    )
                except Exception as e:
                    formatted_exception = f"raise {type(e).__name__}"
                    return_lines.append(
                        f'"{callee_name}" -x "{caller_name}": {formatted_exception}'
                    )
                    exception_to_raise = e
                finally:
                    # This finally block is now INSIDE the 'else',
                    # so it only runs for the first call in a sequence
                    return_lines.append(f'deactivate "{callee_name}"')

                # Create the *new* pending call
                self._pending_call = {
                    "info": current_call_info,
                    "lines": call_lines + return_lines,  # Store all lines
                    "count": 1,
                }

                # Return or re-raise
                if exception_to_raise:
                    raise exception_to_raise

                # If we get here, no exception occurred
                return result

        return wrapper

    def get_diagram(self) -> str:
        """Returns the complete PlantUML diagram string."""
        # Flush any remaining call before finishing
        self._flush_pending_call()
        return "\n".join(self._uml_lines) + "\n@enduml\n"


# --- The Singleton Instance ---
# Import this instance in other modules to share the same trace
global_tracer = PlantUMLTracer()
