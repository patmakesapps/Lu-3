"""Execute tools requested by Lu."""

from .tools import TOOL_FUNCTIONS

def execute_tool(name: str, arguments: dict) -> dict:
    """Run a registered tool and return its result or an error."""
    if not isinstance(name, str) or name not in TOOL_FUNCTIONS:
        return {"error": f"Unknown tool: {name}"}

    if not isinstance(arguments, dict):
        return {"error": "Tool arguments must be a dictionary."}

    function = TOOL_FUNCTIONS[name]

    try:
        return function(**arguments)     
    except Exception as error:
        return {"error": f"{type(error).__name__}:{error}"}       
