"""Send chat messages and tool definitions to llama-server."""

import json
import urllib.request


def request_completion(server_url, config, messages, tools=None):
    payload = {
        "messages": messages,
        "stream": False,
        "max_tokens": config["max_reply_tokens"],
        "temperature": config["temperature"],
        "top_p": config["top_p"],
        "top_k": config["top_k"],
        "repeat_penalty": config["repeat_penalty"],
        # Lu was trained with Qwen3's thinking off; keep it off when chatting.
        "chat_template_kwargs": {"enable_thinking": False},
    }

    if tools:
        payload["tools"] = tools
        payload["tool_choice"] = "auto"
        payload["parallel_tool_calls"] = False

    request = urllib.request.Request(
        f"{server_url}/v1/chat/completions",
        data=json.dumps(payload).encode("utf-8"),
        headers={"Content-Type": "application/json"},
    )

    with urllib.request.urlopen(request, timeout=300) as response:
        result = json.load(response)

    return result["choices"][0]["message"]
