"""Lu's conversation history, age guard, and replies."""
from . import memory
from .age_guard import stated_minor
from .agent import run_agent


class Conversation:
    def __init__(self, config, server_url):
        self.config = config
        self.server_url = server_url
        # Pick up where the last run left off.
        self.history = memory.load_session()
        self.trim()

    def reset(self, child_mode=False):
        memory.start_session(child_mode)
        self.history = []

    def listen(self, user_text):
        """Take in what the person said. Returns True if this turned child mode on.

        Saying they're under 18 is a hard stop: a new session starts, so everything said
        before is forgotten and out of recall, and the child note stays in the system
        prompt until reset. The model was trained with the same note, so it knows what
        it means.
        """
        child_mode_started = False
        if not memory.child_mode and stated_minor(user_text):
            self.reset(child_mode=True)
            child_mode_started = True
        message = {"role": "user", "content": user_text}
        memory.save(message)
        self.history.append(message)
        self.trim()
        return child_mode_started

    def trim(self):
        """Keep the last few exchanges, starting at a user message."""
        user_positions = [
            index
            for index, message in enumerate(self.history)
            if message["role"] == "user"
        ]
        if user_positions:
            keep = self.config["history_exchanges"]
            self.history = self.history[user_positions[-keep:][0]:]

    def reply(self):
        """Run Lu's agent loop using the current conversation."""
        # Same system prompt the model was trained with; llama-server adds the
        # tools section from TOOL_DEFINITIONS, just as in training.
        system_prompt = self.config["system_prompt"]
        if memory.child_mode:
            system_prompt += " " + self.config["child_note"]
        remembered = memory.find_memories(self.history[-1]["content"])
        if remembered:
            system_prompt += " Things you remember: " + " ".join(m["text"] for m in remembered)

        messages = [
            {"role": "system", "content": system_prompt}
        ] + self.history

        text = run_agent(self.server_url, self.config, messages)

        for message in messages[1 + len(self.history):]:
            memory.save(message)
        self.history = messages[1:]
        yield text.strip()
