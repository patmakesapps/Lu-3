"""Tools Lu can use to learn about its environment."""

from datetime import datetime

def get_time() -> dict[str, str]:
    """Return the current time and timezone of the machine running Lu."""
    now = datetime.now().astimezone()

    return {
        "timestamp": now.isoformat(timespec="seconds"),
        "timezone": now.tzname() or "unknown",
    }

def get_machine_info() -> dict[str, str]:
        """Return basic information about the machine running Lu."""
        import platform

        return {
            "hostname": platform.node(),
            "operating_system": platform.system(),
            "os_release": platform.release(),
            "architecture": platform.machine(),
            "python_version": platform.python_version(),
        }


TOOL_FUNCTIONS = {
    "get_time": get_time,
    "get_machine_info": get_machine_info,
}


TOOL_DEFINITIONS = [
    {
        "type": "function",
        "function": {
            "name": "get_time",
            "description": "Get the current local date, time, and timezone.",
            "parameters": {
                "type": "object",
                "properties": {},
                "required": [],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "get_machine_info",
            "description": (
                "Get the hostname, operating system, CPU architecture, "
                "and Python version of the machine running you."
            ),
            "parameters": {
                "type": "object",
                "properties": {},
                "required": [],
            },
        },
    },
]
