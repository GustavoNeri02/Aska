# Estado e roadmap

## Estado atual

**Fase atual:** evolução do CLI com Session Context implementado e Persistent Memory em progresso.

**Última Sprint concluída:** Sprint 1 — primeiro CLI do Aska

**Status da Sprint 1:** `implemented`

### Implementado na Sprint 1

- Repositório, monorepo e configuração inicial com Python, uv, Ruff e Pytest.
- Entry point `uv run aska`.
- Banner e saudação no CLI.
- Leitura de mensagens em loop.
- Entrada vazia ignorada.
- Encerramento com `sair`, `exit`, `quit`, EOF ou `Ctrl+C`.
- Testes do comportamento principal do CLI.
- README e documentação modular inicial.
- Encerramento e entradas de borda cobertos por testes automatizados.

### Evolução posterior à Sprint 1

- Contrato mínimo de provider e adaptador HTTP para Ollama.
- Provider injetado no CLI com tratamento de indisponibilidade.
- Ollama e Gemma 3 12B validados com uma resposta local ponta a ponta.

### Comportamento atual

- Session Context está implementado e usa histórico em memória durante a conversa atual.
- A orquestração de conversa e a construção de contexto estão separadas do CLI; entradas do terminal são convertidas em comandos tipados antes da execução.
- Persistent Memory está `in_progress` e já suporta persistência JSON estruturada com identidade e metadados mínimos, registro explícito por `lembrar:`, remoção explícita por `esquecer:`, edição explícita por `editar memória:`, pesquisa textual por `buscar memória:` e listagem por `memórias`.
- O comportamento atual do CLI não depende mais da resposta placeholder da Sprint 1.

### Incremento atual de memória explícita

O incremento atual de Persistent Memory implementa exclusivamente objetos com `id`, `content`, `source`, `created_at` e `updated_at` em JSON. O CLI continua expondo os comandos atuais e envia somente o conteúdo das memórias ao modelo.

### Limitações atuais do incremento

- Todas as memórias salvas são enviadas em todas as requisições ao modelo.
- Não há seleção por relevância, compactação ou orçamento de tokens.
- JSON continua sendo o armazenamento atual; SQLite é uma evolução provável, ainda não adotada.
- O datasource JSON usa cache por instância e escrita atômica, mas ainda assume um único writer durante a execução. `SqliteMemoryDataSource` permanece `planned`.
- Tipos avançados, seleção semântica e explicabilidade além dos metadados mínimos continuam pendentes.

## Roadmap

| Fase | Nome | Objetivo | Status |
| --- | --- | --- | --- |
| 0 | Foundation | Setup, monorepo, documentação e qualidade | `implemented` |
| 1 | CLI and local conversation | CLI e primeira conversa com modelo local substituível | `implemented` |
| 2 | Session context | Histórico e contexto útil na sessão | `implemented` |
| 3 | Persistent memory | Memória local transparente e consultável | `in_progress` |
| 4 | Tools and capabilities | Registro seguro e primeira capability | `planned` |
| 5 | Knowledge and retrieval | Indexação de documentos, código e informações | `planned` |
| 6 | Desktop interaction | Recursos do computador com permissões e auditoria | `planned` |
| 7 | Vision | Captura e interpretação de tela e imagens | `planned` |
| 8 | Voice | Entrada e resposta por voz local | `planned` |
| 9 | Persistent presence | Experiência contínua, possivelmente com avatar | `planned` |

O roadmap expressa direção, não compromisso de implementação antecipada. Cada fase deve ser refinada quando se tornar o próximo incremento concreto.
