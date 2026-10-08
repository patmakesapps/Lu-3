# Notes for Claude Code

What Claude Code kept in its local memory for this project, copied here before moving to a new
laptop (2026-10-08). On a new machine, point Claude Code at this file to pick up where things
left off.

## How to work with Pat

When Pat hands over a specific code change (often pasted step by step from a tutor), make
exactly that change and stop. Don't run tests, hit llama-server, read logs, or investigate
further unless asked. Confirm in a line or two and at most offer a next step.

Why: on 2026-10-07 Pat interrupted with "i didnt ask you to test" after a debug-print edit to
`lu3/model.py` was followed by reading logs and curling the server. Pat works through the setup
one step at a time and wants to run things themselves.

## Where the project stands (2026-10-08)

- **Model:** the memory-tools round (trained on all seven runtime tools: `get_time`,
  `get_machine_info`, `remember`, `recall`, `list_memories`, `update_memory`, `forget`) is on
  Hugging Face at `patkearney/lu3-qwen3-4b`. The runtime uses `gguf/lu3-q4_k_m.gguf`, downloaded
  from `software/` into `software/models/gguf/` (see `software/README.md`).
- **Hands-on test:** tool calling works well ("tool calling is working real well"). A long
  red-team chat showed it going along with drinking, drugs, and driving before refusing, so it
  is usable with tools for now but not ready for a home without a filter in front of it.
- **Next training run:** waits until the Jetson is set up and the robot's production tools
  exist, so the model is trained once on the real tool set. The current model stays in use until
  then. The plan is in the `lu3-finetune` repo's README under "Next round": safety first
  (drinking, drugs, and driving; violence as a precaution; slurs), then memory and tools,
  personality, and runtime fixes.
- **Training repo:** `lu3-finetune` (github.com/patmakesapps/lu-3-finetune). Its README describes
  the data and method; the sim and checker scripts from the last data round were scratch files
  and are gone.

## Known runtime issues (not fixed yet)

- `forget` deletes the memory but leaves the fact in the message archive, so `recall` can still
  find it.
- Memory search matches whole words with no stemming ("weekend" doesn't find "Saturday").
- The chat shows `[tool] <name>` but not the arguments.
- An unknown `/` command (like `/restart`) is sent to Lu as a chat message instead of being
  rejected.
- Lu's memory database (`software/data/lu3.db`) is not kept in git; Lu starts fresh on each new
  machine, which is intended for the Jetson.
