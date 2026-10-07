"""Coordinate model responses and tool execution."""

import json

from .executor import execute_tool
from .model import request_completion
from .tools import TOOL_DEFINITIONS


def run_agent(server_url, config, messages):
    for _ in range(4):
        message = request_completion(
            server_url, config, messages, tools=TOOL_DEFINITIONS
        )
        if message.get("content"):
            message["content"] = message["content"].strip()
        messages.append(message)

        tool_calls = message.get("tool_calls") or []
        if not tool_calls:
            return message.get("content") or ""

        for call in tool_calls:
            name = call["function"]["name"]
            print(f"\n[tool] {name}", flush=True)

            try:
                arguments = json.loads(
                    call["function"].get("arguments") or "{}"
                )
            except (json.JSONDecodeError, TypeError):
                result = {"error": "Tool arguments were not valid JSON."}
            else:
                result = execute_tool(name, arguments)

            messages.append({
                "role": "tool",
                "tool_call_id": call["id"],
                "content": json.dumps(result),
            })

    reply = "I couldn't finish that within my tool-call limit."
    messages.append({"role": "assistant", "content": reply})
    return reply