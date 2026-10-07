"""Run Lu-3. For now this is a typed chat; voice (speech-to-text and text-to-speech) comes next.

    python -m lu3
"""
import argparse
import json
from pathlib import Path

from . import memory
from .brain import Conversation
from .server import LlamaServer

software_dir = Path(__file__).resolve().parent.parent

with (Path(__file__).resolve().parent / "config.json").open(encoding="utf-8") as file:
    config = json.load(file)

parser = argparse.ArgumentParser(prog="lu3", description="Run Lu-3.")
parser.add_argument("--model", default=str(software_dir / config["model"]), help="GGUF model file.")
parser.add_argument("--server", default=config["llama_server"], help="Path to llama-server.")
parser.add_argument("--port", type=int, default=config["port"])
args = parser.parse_args()

server = LlamaServer(args.server, args.model, args.port, config["context_size"],
                     software_dir / "logs" / "llama-server.log")

print(f"Starting llama-server with {Path(args.model).name} ...")
memory.connect(software_dir / config["memory_db"])
with server:
    conversation = Conversation(config, server.url)
    print("Lu is listening. Commands: /reset, /quit")

    while True:
        try:
            user_text = input("\nYou: ").strip()
        except (EOFError, KeyboardInterrupt):
            print()
            break

        if not user_text:
            continue
        if user_text in ("/quit", "/exit"):
            break
        if user_text == "/reset":
            conversation.reset()
            print("(history cleared)")
            continue

        if conversation.listen(user_text):
            print("(under 18 stated: history cleared, child mode on)")

        print("Lu: ", end="", flush=True)
        for piece in conversation.reply():
            print(piece, end="", flush=True)
        print()
