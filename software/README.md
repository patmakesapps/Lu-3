# Lu-3 software

The runtime that runs on the robot (a Jetson Orin Nano 8GB). It talks to the fine-tuned Lu-3
model through llama.cpp's `llama-server`, keeps the conversation, applies the age guard, and
runs an agent loop that lets Lu call tools. Right now it is a typed chat; speech-to-text and
text-to-speech come next.

The model is trained in a separate repo (`lu3-finetune`). The system prompt and child note in
`lu3/config.json` must match the ones used in training, and `lu3/age_guard.py` is the same
file the training repo uses.

## Setup (Windows)

1. Install llama.cpp so `llama-server` is on your PATH (Windows: `winget install llama.cpp`), or
   set `llama_server` in `lu3/config.json` to its full path.
2. Download the model (it lands in `models/gguf/lu3-q4_k_m.gguf`):

   ```
   hf download patkearney/lu3-qwen3-4b gguf/lu3-q4_k_m.gguf --local-dir models
   ```

   The repo is private, so set `HF_TOKEN` first.

No Python packages are needed beyond the standard library.

The model is not kept in git (it is about 2.5 GB); `models/` and `logs/` are ignored.

## Setup (Jetson)

On JetPack 6, which ships CUDA:

1. Clone this repo.
2. Build llama.cpp with CUDA. The Orin's GPU is compute capability 8.7:

   ```
   sudo apt install -y git cmake build-essential
   export PATH=/usr/local/cuda/bin:$PATH
   git clone https://github.com/ggml-org/llama.cpp ~/llama.cpp
   cd ~/llama.cpp
   cmake -B build -DGGML_CUDA=ON -DCMAKE_CUDA_ARCHITECTURES=87
   cmake --build build --config Release -j$(nproc) --target llama-server
   ```

   Then add `~/llama.cpp/build/bin` to your PATH, or set `llama_server` in `lu3/config.json`
   to `/home/<you>/llama.cpp/build/bin/llama-server`.
3. Download the model. The GGUF file is the same one used on Windows:

   ```
   pip3 install -U huggingface_hub
   export HF_TOKEN=<your token>
   hf download patkearney/lu3-qwen3-4b gguf/lu3-q4_k_m.gguf --local-dir models
   ```

4. Run `python3 -m lu3`, then check `logs/llama-server.log` for a line saying the model's
   layers were offloaded to CUDA. If they were not, llama.cpp was built without CUDA and the
   model is running on the CPU, which will be slow.

## Run

From this folder:

```
python -m lu3
```

`--model` and `--server` override the paths in `lu3/config.json`. If a llama-server is
already running on the configured port, Lu uses it instead of starting another. Server
output goes to `logs/llama-server.log`.

Commands: `/reset` clears the conversation (and child mode), `/quit` exits. When Lu calls a
tool, the chat prints `[tool] <name>` before the reply.

## Tools

Each turn goes through an agent loop: the reply is requested with the tool definitions
attached, any tool calls are run and their results sent back, and this repeats (up to four
rounds) until Lu answers in plain text. llama-server is started with `--jinja` so it builds
the tools section of the prompt from the model's chat template, the same way it was built in
training. Replies are no longer streamed, since the loop needs the whole message to see if it
contains tool calls.

The tools so far are read-only:

- `get_time`: the local date, time, and timezone.
- `get_machine_info`: hostname, operating system, CPU architecture, and Python version.

To add a tool, write the function in `lu3/tools.py`, add it to `TOOL_FUNCTIONS`, and add its
schema to `TOOL_DEFINITIONS`.

Status: the plumbing works, but the current model does not reliably call tools. Adding an
extra system prompt to push it toward tool calls was tried and removed, because the system
prompt has to match training. The model needs to be retrained with tool-calling examples.

## Layout

- `lu3/__main__.py`: the chat loop.
- `lu3/brain.py`: conversation history, age guard, and system prompt; hands each turn to the agent.
- `lu3/agent.py`: the agent loop (request a reply, run tool calls, repeat).
- `lu3/model.py`: sends messages and tool definitions to llama-server's chat completions API.
- `lu3/tools.py`: the tool functions and their definitions.
- `lu3/executor.py`: runs a requested tool by name and turns errors into results Lu can read.
- `lu3/server.py`: starts and stops llama-server.
- `lu3/age_guard.py`: detects a stated age under 18 (`python -m lu3.age_guard` runs its checks).
- `lu3/config.json`: model path, server port, system prompt, child note, sampling settings.
