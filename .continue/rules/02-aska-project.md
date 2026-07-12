---
name: Aska project rules
description: Regras obrigatórias para trabalhar no projeto Aska
alwaysApply: true
---

# Projeto Aska

Antes de responder sobre arquitetura ou implementação:

1. Leia `AGENTS.md`.
2. Leia `docs/README.md` e os documentos relacionados à tarefa.
3. Inspecione o código afetado antes de sugerir ou realizar mudanças.
6. Quando houver conflito documental, siga a precedência definida em
   `docs/README.md`.

## Execução

- Não crie abstrações ou módulos vazios antecipadamente.
- Não adicione dependências sem explicar o problema concreto resolvido.
- Valide implementações com testes e Ruff quando aplicável.
- Não execute ações destrutivas silenciosamente.
- Se o pedido for apenas de análise, não altere arquivos.

## Comunicação

- Responda em português do Brasil.
- Ao explicar particularidades de Python, compare com Dart quando isso ajudar.
- Apresente primeiro o resultado ou ação prática.
- Ao concluir uma implementação, informe:
  - o que mudou;
  - por que mudou;
  - quais validações foram executadas;
  - o que permanece pendente.

