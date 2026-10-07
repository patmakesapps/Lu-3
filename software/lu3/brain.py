"""Lu's side of a conversation: history, the age guard, and streamed replies from llama-server."""
import json
import urllib.request

from .age_guard import stated_minor


class Conversation:
    def __init__(self, config, server_url):
        self.config = config
        self.server_url = server_url
        self.reset()

    def reset(self):
        self.history = []
        self.child_mode = False

    def listen(self, user_text):
        """Take in what the person said. Returns True if this turned child mode on.

        Saying they're under 18 is a hard stop: everything said before is forgotten,
        and the child note stays in the system prompt until reset. The model was
        trained with the same note, so it knows what it means.
        """
        child_mode_started = False
        if not self.child_mode and stated_minor(user_text):
            self.history, self.child_mode = [], True
            child_mode_started = True
        self.history.append({"role": "user", "content": user_text})
        self.history = self.history[-(self.config["history_exchanges"] * 2 - 1):]
        return child_mode_started

    def reply(self):
        """Stream Lu's reply to the last thing heard, as pieces of text.

        The full reply is added to the history once the stream ends.
        """
        system_prompt = self.config["system_prompt"]
        if self.child_mode:
            system_prompt += " " + self.config["child_note"]

        payload = {
            "messages": [{"role": "system", "content": system_prompt}] + self.history,
            "stream": True,
            "max_tokens": self.config["max_reply_tokens"],
            "temperature": self.config["temperature"],
            "top_p": self.config["top_p"],
            "top_k": self.config["top_k"],
            "repeat_penalty": self.config["repeat_penalty"],
            # Lu was trained with Qwen3's thinking off; keep it off when chatting.
            "chat_template_kwargs": {"enable_thinking": False},
        }
        request = urllib.request.Request(
            f"{self.server_url}/v1/chat/completions",
            data=json.dumps(payload).encode("utf-8"),
            headers={"Content-Type": "application/json"},
        )

        pieces = []
        with urllib.request.urlopen(request, timeout=300) as response:
            for line in response:
                line = line.decode("utf-8").strip()
                if not line.startswith("data: ") or line == "data: [DONE]":
                    continue
                choices = json.loads(line[len("data: "):]).get("choices") or [{}]
                piece = choices[0].get("delta", {}).get("content")
                if piece:
                    pieces.append(piece)
                    yield piece

        self.history.append({"role": "assistant", "content": "".join(pieces).strip()})
