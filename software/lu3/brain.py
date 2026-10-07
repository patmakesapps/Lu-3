"""Lu's conversation history, age guard, and replies."""
from .age_guard import stated_minor
from .model import request_completion


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
        """Generate a reply using the current conversation and child mode."""
        system_prompt = self.config["system_prompt"]
        if self.child_mode:
            system_prompt += " " + self.config["child_note"]

        messages = [
            {"role": "system", "content": system_prompt}
        ] + self.history

        message = request_completion(
            self.server_url, self.config, messages
        )
        text = (message.get("content") or "").strip()

        self.history.append({"role": "assistant", "content": text})
        yield text
