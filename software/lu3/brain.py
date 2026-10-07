"""Lu's conversation history, age guard, and replies."""
from .age_guard import stated_minor
from .agent import run_agent


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
        user_positions = [
            index
            for index, message in enumerate(self.history)
            if message["role"] == "user"
        ]
        keep = self.config["history_exchanges"]
        if len(user_positions) > keep:
            self.history = self.history[user_positions[-keep]:]
        return child_mode_started

    def reply(self):
        """Run Lu's agent loop using the current conversation."""
        system_prompt = self.config["system_prompt"]
        system_prompt += (
            " You can request tools through the tool-calling interface."
            " When asked for the current date or time, call get_time."
            " When asked about the machine running you, call get_machine_info."
            " Wait for the tool result before answering those questions."
            " Never invent a tool result or claim execution without a result."
            " Use structured tool calls, not placeholders in your spoken reply."
            " The short spoken style and no-symbols rule apply only to your"
            " final answer, not to structured tool calls."
        )
        if self.child_mode:
            system_prompt += " " + self.config["child_note"]

        messages = [
            {"role": "system", "content": system_prompt}
        ] + self.history

        text = run_agent(self.server_url, self.config, messages)

        self.history = messages[1:]
        yield text.strip()
