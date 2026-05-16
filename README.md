# Minimal Menu-Based Ollama Agent

A simple Python agent that avoids fragile native tool-calling. The model only chooses one action from the environment's admissible-command menu; Python owns all environment calls and success checks.

Features:

- Ollama via raw HTTP `/api/generate`
- No LangGraph tool calls / XML function-call parsing
- Stateful mini-ALFWorld command integration
- Menu validation + retry + deterministic fallback

## Prerequisites

Install and run Ollama, then pull a model:

```powershell
ollama pull qwen3.5:0.8b
```

## Run

Run the menu-based agent:

```powershell
uv run agent
```

It resets the environment by default. To continue from the current persisted state:

```powershell
uv run agent --no-reset
```

You can choose another Ollama model with `--model`:

```powershell
uv run agent --model mistral
```
