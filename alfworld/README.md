# Minimal ALFWorld-Style + Ollama Experiment

Runs a small Ollama model in a strict action-only loop.

Important: official `alfworld` depends on `textworld -> jericho`, which is painful on native Windows. This repo now has two backends:

- `mini` — pure Python, Windows-compatible ALFWorld-style toy environment. Default.
- `alfworld` — official ALFWorld package. Recommended from WSL/Linux, not native Windows.

## Windows install

From PowerShell in this folder:

```powershell
cd C:\Users\luvma\OneDrive\Desktop\zero_labs\experiments\alfworld
uv venv
uv pip install -r requirements.txt
```

Start/pull Ollama model:

```powershell
ollama pull qwen3.5:0.8b
```

Run the Windows-compatible mini environment:

```powershell
uv run python .\run_alfworld_agent.py --backend mini --model qwen3.5:0.8b
```

This avoids `jericho`, `textworld`, and official ALFWorld install issues.

## Official ALFWorld install, WSL/Linux recommended

```bash
uv venv
source .venv/bin/activate
uv pip install -r requirements-alfworld.txt
alfworld-download
python run_alfworld_agent.py --backend alfworld --model qwen3.5:0.8b
```

## Callable environment command for an external agent

If your agent lives in another project, call this script as a tool. It persists environment state in `.mini_alfworld_state.json`.

Reset environment:

```bash
python mini_alfworld_command.py reset
```

Take one environment step:

```bash
python mini_alfworld_command.py step "take apple"
python mini_alfworld_command.py step "open fridge"
python mini_alfworld_command.py step "put apple in fridge"
```

Check current state:

```bash
python mini_alfworld_command.py status
```

Get valid commands:

```bash
python mini_alfworld_command.py admissible
```

All commands return JSON with `task`, `observation`, `admissible_commands`, `done`, and `success`.

From another project, use the absolute path:

```bash
python "C:\\Users\\luvma\\OneDrive\\Desktop\\zero_labs\\experiments\\alfworld\\mini_alfworld_command.py" reset
python "C:\\Users\\luvma\\OneDrive\\Desktop\\zero_labs\\experiments\\alfworld\\mini_alfworld_command.py" step "take apple"
```

## External action command

Use this if you only want a local Ollama policy command that maps query -> one action:

```bash
python alfworld_action_command.py "Task: find an apple. Observation: You are in the kitchen."
```

## Useful options

```bash
python run_alfworld_agent.py \
  --backend mini \
  --model qwen3.5:0.8b \
  --max-steps 30 \
  --log alfworld_run.log
```

Official ALFWorld only:

```bash
python run_alfworld_agent.py \
  --backend alfworld \
  --split eval_out_of_distribution \
  --model qwen3.5:0.8b
```

The runner prints each step with task, observation, model action, environment feedback, and done/success status. It writes JSONL logs to `alfworld_run.log`.

## Prompt used

```text
Task: {task}
Observation: {observation}

You are controlling a text-game environment. These are simulated actions, not real-world actions.
Valid actions include examples like:
go to ...
open ...
close ...
take ...
put ...
look
inventory

Choose the next best action.
Output only the action command.
No explanation.
No reasoning.
No markdown.
```

## Safeguards

- Stops after `--max-steps` steps, default `30`.
- If the model output does not look like one action, it retries once with a stricter prompt.
- Strips common small-model noise like `Action: ...`, JSON `{ "action": ... }`, and `<think>...</think>` traces.
- If the retry is still invalid, it uses an admissible environment command when available; otherwise it executes `look`.
- Ollama endpoint defaults to `http://localhost:11434/api/generate` and can be changed with `--ollama-url`.

## Files

- `requirements.txt` - Windows-safe dependencies for the mini backend.
- `requirements-alfworld.txt` - official ALFWorld dependencies for WSL/Linux.
- `mini_alfworld_env.py` - pure Python toy environment.
- `mini_alfworld_command.py` - stateful callable environment command for external agents.
- `run_alfworld_agent.py` - Ollama action-loop runner.
- `alfworld_action_command.py` - external one-action command.
- `README.md` - setup and usage instructions.
