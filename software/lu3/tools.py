"""Tools Lu can use to learn about its environment."""

from datetime import datetime

from . import memory

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
    "remember": memory.remember,
    "recall": memory.recall,
    "update_memory": memory.update_memory,
    "forget": memory.forget,
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
    {
        "type": "function",
        "function": {
            "name": "remember",
            "description": "Save a lasting fact, preference, person, project, or decision to remember later.",
            "parameters": {
                "type": "object",
                "properties": {
                    "text": {"type": "string", "description": "The thing to remember, as a short sentence."},
                },
                "required": ["text"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "recall",
            "description": "Search saved memories and past conversations.",
            "parameters": {
                "type": "object",
                "properties": {
                    "query": {"type": "string", "description": "Words to search for."},
                },
                "required": ["query"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "update_memory",
            "description": "Correct a saved memory.",
            "parameters": {
                "type": "object",
                "properties": {
                    "id": {"type": "integer", "description": "The memory's id, from recall."},
                    "text": {"type": "string", "description": "The corrected memory."},
                },
                "required": ["id", "text"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "forget",
            "description": "Delete a saved memory.",
            "parameters": {
                "type": "object",
                "properties": {
                    "id": {"type": "integer", "description": "The memory's id, from recall."},
                },
                "required": ["id"],
            },
        },
    },
]
