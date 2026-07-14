# Aska

Aska é uma IA pessoal local, conversacional e progressivamente multimodal. O projeto prioriza privacidade, independência de provider e controle do usuário sobre seus dados.

## Estado atual

O CLI conversa com o modelo local por meio do Ollama, mantém o histórico da sessão, oferece memória persistente explícita em JSON e pode ler um arquivo textual conhecido ou descobrir caminhos de arquivos com segurança dentro do workspace. Conteúdo e listagens são usados somente como contexto temporário. Persistent Memory está `implemented`; Tools and capabilities está `in_progress` com esse recorte read-only.

Veja o [estado detalhado e roadmap](docs/project/roadmap.md).

## Requisitos

- Python 3.13 ou superior;
- [uv](https://docs.astral.sh/uv/).

## Preparação

```bash
uv sync
```

O `uv` cumpre aqui um papel próximo ao de `flutter pub get`, além de gerenciar o ambiente virtual e a versão do Python usada pelo projeto.

## Modelo local

O primeiro provider suportado é o [Ollama](https://docs.ollama.com/windows), cuja API local deve estar disponível em `http://localhost:11434`. O modelo padrão para a máquina principal do projeto é `gemma3:12b` e pode ser alterado por variável de ambiente:

```powershell
$env:ASKA_MODEL = "gemma3:12b"
```

O endereço do Ollama também pode ser alterado com `ASKA_OLLAMA_URL`.

O workspace permitido para leitura de arquivos usa o diretório atual por padrão e pode ser configurado explicitamente:

```powershell
$env:ASKA_WORKSPACE_ROOT = "D:\Projetos\Aska"
```

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
