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
4. Diferencie explicitamente `planned`, `in_progress`, `implemented`,
   `superseded` e `rejected`.
5. Não invente arquivos, funcionalidades, comandos executados ou estado do
   repositório.
6. Quando houver conflito documental, siga a precedência definida em
   `docs/README.md`.

## Execução

- Prefira mudanças pequenas, delimitadas e verificáveis.
- Não crie abstrações ou módulos vazios antecipadamente.
- Não adicione dependências sem explicar o problema concreto resolvido.
- Preserve alterações existentes e evite refatorações não relacionadas.
- Valide implementações com testes e Ruff quando aplicável.
- Não execute ações destrutivas silenciosamente.
- Se o pedido for apenas de análise, não altere arquivos.
- Se houver ambiguidade que mude materialmente a implementação, peça
  esclarecimento antes de editar.

## Comunicação

- Responda em português do Brasil.
- Trate Gustavo como desenvolvedor experiente em Flutter e Dart.
- Ao explicar particularidades de Python, compare com Dart quando isso ajudar.
- Apresente primeiro o resultado ou ação prática.
- Ao concluir uma implementação, informe:
  - o que mudou;
  - por que mudou;
  - quais validações foram executadas;
  - o que permanece pendente.

## Uso de ferramentas

- Quando a informação puder ser obtida no repositório, inspecione os arquivos em
  vez de pedir que o usuário copie seu conteúdo.
- Para falhas de teste, localize e execute o teste relacionado quando houver
  acesso ao terminal.
- Não peça caminhos, erros ou conteúdo que possam ser descobertos com as
  ferramentas disponíveis.
- Se uma ferramenta necessária não estiver disponível, informe especificamente
  qual acesso está ausente.
