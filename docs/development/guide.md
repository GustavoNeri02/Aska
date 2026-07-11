# Guia de desenvolvimento

## Stack

- Python 3.13 ou superior.
- `uv` para ambiente, dependências e execução.
- Ruff para lint e formatação.
- Pytest para testes.
- Tipagem moderna do Python.
- `Protocol` quando houver contrato arquitetural real.
- `dataclass` para estruturas simples quando apropriado.

`pyproject.toml` concentra metadados, dependências e configuração de ferramentas, cumprindo parte do papel do `pubspec.yaml`. O ambiente virtual isola o interpretador e as dependências do projeto.

## Comandos

```bash
uv sync
uv run ruff format .
uv run ruff check .
uv run pytest
uv run aska
```

## Diretrizes de código

- Prefira a solução mais simples que preserve evolução incremental.
- Use nomes claros, responsabilidades pequenas e pontos de entrada enxutos.
- Injete dependências por parâmetros enquanto isso for suficiente.
- Evite estado global, singletons e lógica concentrada em `main.py`.
- Crie contratos somente diante de duas implementações ou de um limite arquitetural real.
- Escreva testes para comportamentos importantes e tratamento de erro proporcional ao estágio.
- Use tipagem sem complexidade desnecessária.
- Preserve os comandos definidos no `pyproject.toml`.
- Não adicione dependências sem explicar o problema resolvido.
- Não refatore áreas não relacionadas.
- Entregue alterações pequenas, revisáveis e executáveis.

Antes de criar uma abstração, confirme qual problema atual ela resolve, se simplifica o sistema, se é necessária agora e se pode ser adicionada depois sem retrabalho relevante.

## Tecnologias não adotadas por padrão

Não introduzir automaticamente LangChain, LlamaIndex, CrewAI, AutoGen, frameworks grandes de agentes, FastAPI, Pydantic, banco vetorial, container próprio de DI, event bus, service registry ou múltiplos agentes.

Cada tecnologia deve entrar somente quando resolver uma necessidade concreta e documentada.

## Processo

```text
entender a necessidade
→ consultar documentação e código
→ propor uma mudança pequena
→ implementar
→ testar
→ executar lint
→ atualizar a documentação necessária
→ registrar decisões duradouras
```

Cada etapa deve terminar com algo funcionando ou verificável. Priorize, nesta ordem: correção, segurança, clareza, simplicidade, testabilidade, manutenção, modularidade, performance e flexibilidade futura.

## Git

Use Conventional Commits, por exemplo:

```text
feat(cli): add initial conversation loop
feat(models): add local provider contract
test(memory): cover explicit memory storage
docs(architecture): record provider abstraction
fix(cli): handle interrupted input
refactor(context): extract context builder
```

Quando uma decisão substituir outra, registre a nova justificativa e marque a anterior como `superseded`, sem apagar silenciosamente o histórico relevante.
