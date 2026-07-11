# Aska

Aska é uma IA pessoal local, conversacional e progressivamente multimodal. O projeto prioriza privacidade, independência de provider e controle do usuário sobre seus dados.

## Estado atual

A Sprint 1 contém um CLI funcional que exibe uma saudação, recebe mensagens, ignora entradas vazias, encerra de forma controlada e responde com um placeholder. Modelo local, contexto, memória persistente e capabilities ainda estão planejados.

Veja o [estado detalhado e roadmap](docs/project/roadmap.md).

## Requisitos

- Python 3.13 ou superior;
- [uv](https://docs.astral.sh/uv/).

## Preparação

```bash
uv sync
```

O `uv` cumpre aqui um papel próximo ao de `flutter pub get`, além de gerenciar o ambiente virtual e a versão do Python usada pelo projeto.

## Executar

```bash
uv run aska
```

Também é possível executar diretamente o pacote do CLI:

```bash
uv run python -m apps.cli
```

## Qualidade

```bash
uv run ruff format .
uv run ruff check .
uv run pytest
```

## Documentação

O [índice da documentação](docs/README.md) organiza a visão do produto, arquitetura, memória, desenvolvimento, roadmap e decisões. As instruções para colaboração estão em [AGENTS.md](AGENTS.md).

## Estrutura do repositório

```text
apps/          interfaces executáveis, inicialmente o CLI
packages/      bibliotecas internas compartilhadas
capabilities/  capacidades independentes futuras
docs/          documentação técnica e de produto
scripts/       automações de desenvolvimento e manutenção
tests/         testes compartilhados e de integração
data/          dados locais, memória, logs, cache e modelos
```
