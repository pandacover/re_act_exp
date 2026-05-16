# ReAct Agent Experiment 

## Problem statement
Can a tiny model like `qwen3.5:0.8b` solve a simple embodied text game if given access to a simulated environment?

## Task
> *Note: This is not an official ALFWorld task but a simplified version for testing purposes.*

put the apple in the fridge

## Conclusion
Even a tiny model like `qwen3.5:0.8b` can solve a simple embodied text game with the help of ReAct strategy.

## Testing out for yourself

### Prerequisites

Install and run Ollama, then pull a model:

```powershell
ollama pull qwen3.5:0.8b
```

### Run

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

## Research papers which inspired this project
Paper: ReAct: Synergizing Reasoning and Acting in Language Models  
arXiv: https://arxiv.org/abs/2210.03629
```bibtex
@article{yao2022react,
  title={ReAct: Synergizing Reasoning and Acting in Language Models},
  author={Yao, Shunyu and Zhao, Jeffrey and Yu, Dian and Du, Nan and Shafran, Izhak and Narasimhan, Karthik and Cao, Yuan},
  journal={arXiv preprint arXiv:2210.03629},
  year={2022}
}
```
