---
name: Python project rules
description: Convenções aplicáveis ao código Python e aos testes do Aska
globs: ["**/*.py", "pyproject.toml"]
alwaysApply: false
---

# Python

- Use Python 3.13 e a tipagem já adotada pelo projeto.
- Preserve os comandos e configurações definidos no `pyproject.toml`.
- Use `Protocol` apenas diante de um limite arquitetural real.
- Use `dataclass` apenas quando simplificar um modelo de dados concreto.
- Injete dependências por parâmetros enquanto isso for suficiente.
- Evite estado global e singletons.
- Escreva testes Pytest proporcionais ao comportamento alterado.
- Para validar, considere:

```bash
uv run ruff format .
uv run ruff check .
uv run pytest
