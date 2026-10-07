# Lu-3 software

The runtime that runs on the robot (a Jetson Orin Nano 8GB). It talks to the fine-tuned Lu-3
model through llama.cpp's `llama-server`, keeps the conversation, and applies the age guard.
Right now it is a typed chat; speech-to-text and text-to-speech come next, then tool calling.

The model is trained in a separate repo (`lu3-finetune`). The system prompt and child note in
`lu3/config.json` must match the ones used in training, and `lu3/age_guard.py` is the same
file the training repo uses.

## Setup

1. Install llama.cpp so `llama-server` is on your PATH (Windows: `winget install llama.cpp`), or
   set `llama_server` in `lu3/config.json` to its full path.
2. Download the model (it lands in `models/gguf/lu3-q4_k_m.gguf`):

   ```
   hf download patkearney/lu3-qwen3-4b gguf/lu3-q4_k_m.gguf --local-dir models
   ```

   The repo is private, so set `HF_TOKEN` first.

No Python packages are needed beyond the standard library.

## Run

From this folder:

```
python -m lu3
```

`--model` and `--server` override the paths in `lu3/config.json`. If a llama-server is
already running on the configured port, Lu uses it instead of starting another. Server
output goes to `logs/llama-server.log`.

Commands: `/reset` clears the conversation (and child mode), `/quit` exits.

## Layout

- `lu3/__main__.py`: the chat loop.
- `lu3/brain.py`: conversation history, age guard, and streamed replies from llama-server.
- `lu3/server.py`: starts and stops llama-server.
- `lu3/age_guard.py`: detects a stated age under 18 (`python -m lu3.age_guard` runs its checks).
- `lu3/config.json`: model path, server port, system prompt, child note, sampling settings.
