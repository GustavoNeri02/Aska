# Estado e roadmap

## Estado atual

**Fase:** 1 — CLI and local conversation

**Última Sprint concluída:** Sprint 1 — primeiro CLI do Aska

**Status da Sprint 1:** `implemented`

### Implementado

- Repositório, monorepo e configuração inicial com Python, uv, Ruff e Pytest.
- Entry point `uv run aska`.
- Banner e saudação no CLI.
- Leitura de mensagens em loop.
- Entrada vazia ignorada.
- Encerramento com `sair`, `exit`, `quit`, EOF ou `Ctrl+C`.
- Resposta placeholder informando que não há modelo conectado.
- Testes do comportamento principal do CLI.
- README e documentação modular inicial.
- Encerramento e entradas de borda cobertos por testes automatizados.
- Contrato mínimo de provider e adaptador HTTP para Ollama.
- Provider injetado no CLI com tratamento de indisponibilidade.
- Ollama e Gemma 3 12B validados com uma resposta local ponta a ponta.

### Próximo incremento

Iniciar o contexto da sessão mantendo o histórico apenas em memória, sem antecipar persistência.

## Roadmap

| Fase | Nome | Objetivo | Status |
| --- | --- | --- | --- |
| 0 | Foundation | Setup, monorepo, documentação e qualidade | `implemented` |
| 1 | CLI and local conversation | CLI e primeira conversa com modelo local substituível | `implemented` |
| 2 | Session context | Histórico e contexto útil na sessão | `planned` |
| 3 | Persistent memory | Memória local transparente e consultável | `planned` |
| 4 | Tools and capabilities | Registro seguro e primeira capability | `planned` |
| 5 | Knowledge and retrieval | Indexação de documentos, código e informações | `planned` |
| 6 | Desktop interaction | Recursos do computador com permissões e auditoria | `planned` |
| 7 | Vision | Captura e interpretação de tela e imagens | `planned` |
| 8 | Voice | Entrada e resposta por voz local | `planned` |
| 9 | Persistent presence | Experiência contínua, possivelmente com avatar | `planned` |

O roadmap expressa direção, não compromisso de implementação antecipada. Cada fase deve ser refinada quando se tornar o próximo incremento concreto.
