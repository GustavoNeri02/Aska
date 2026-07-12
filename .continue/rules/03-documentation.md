---
name: Aska documentation rules
description: Regras para atualizar a documentação autoritativa do Aska
globs: ["README.md", "AGENTS.md", "docs/**/*.md"]
alwaysApply: false
---

# Documentação do Aska

- Consulte `docs/README.md` para identificar o documento responsável pelo assunto.
- Evite repetir a mesma informação em vários documentos.
- Use os estados `planned`, `in_progress`, `implemented`, `superseded` e
  `rejected` de acordo com o código verificável.
- Não descreva funcionalidades planejadas como existentes.
- Mudanças arquiteturais devem atualizar o documento temático responsável.
- Decisões duradouras devem ser registradas em `docs/project/decisions.md`.
- Quando uma decisão for substituída, preserve seu histórico e marque-a como
  `superseded`.
- Atualize `docs/project/roadmap.md` somente quando o estado real da
  implementação mudar.
- Preserve português do Brasil, links relativos e a estrutura Markdown existente.
