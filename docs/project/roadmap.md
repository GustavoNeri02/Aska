# Estado e roadmap

## Estado atual

**Fase atual:** Tools and capabilities está `in_progress` com operações read-only confinadas ao workspace para ler um arquivo conhecido e descobrir caminhos.

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
- O modelo carregado pelo Ollama é descarregado via API ao encerrar o CLI, respeitando o servidor configurado por `ASKA_OLLAMA_URL`.
- O CLI exibe um loading enquanto conecta ao Ollama e carrega o modelo no início.
- O núcleo conversacional envia identidade, histórico e mensagem atual com papéis estruturados e independentes do modelo.
- Mudanças naturais do nome de Gustavo usam padrões determinísticos ou interpretação limitada por modelo para gerar uma proposta; confirmação e edição por ID e snapshot permanecem locais.
- Pedidos naturais explícitos de memorização usam padrões determinísticos ou interpretação limitada por modelo para gerar uma proposta; somente a confirmação local aciona `MemoryService.add()`.
- Pedidos naturais explícitos de exclusão selecionam candidatas localmente e somente a confirmação aciona exclusão por ID e snapshot.
- Pedidos com caminho explícito usam extração determinística; variações naturais de leitura e pedidos de descoberta passam por gate e interpretação estruturada. Caminhos, permissões e acesso são validados localmente antes de o contexto temporário ser criado.

### Comportamento atual

- Session Context está implementado e usa histórico em memória com papéis `user` e `assistant` durante a conversa atual; a identidade mínima do Aska é enviada como mensagem `system`.
- A orquestração de conversa e a construção de contexto estão separadas do CLI; entradas do terminal são convertidas em comandos tipados antes da execução.
- Persistent Memory está `implemented` com persistência JSON estruturada, identidade e metadados mínimos, registro explícito por `lembrar:`, remoção explícita por `esquecer:`, edição explícita por `editar memória:`, pesquisa textual por `buscar memória:` e listagem por `memórias`.
- O fluxo natural está implementado para alteração do nome e criação, edição ou exclusão explícita de uma memória. Padrões exatos evitam chamadas ao modelo quando disponíveis e gates separados limitam a interpretação de paráfrases; o modelo apenas propõe, enquanto seleção, confirmação e persistência permanecem locais. Captura automática e pedidos genéricos mais amplos continuam `planned`.
- O comportamento atual do CLI não depende mais da resposta placeholder da Sprint 1.
- As capabilities de filesystem leem um único arquivo UTF-8 conhecido de até 64 KiB ou listam caminhos com profundidade e quantidade limitadas dentro de `ASKA_WORKSPACE_ROOT`; conteúdo e listagens não entram no histórico e são tratados como dados não confiáveis.

### Incremento atual da Fase 4

O recorte read-only atual de Tools and capabilities está `implemented`: `ReadTextFileCapability` lê um arquivo textual conhecido, e `ListFilesCapability` descobre caminhos relativos sem ler conteúdo. Ambas aplicam confinamento local ao workspace e retornam resultados tipados; a listagem também limita profundidade e resultados e ignora diretórios de infraestrutura conhecidos. `NaturalFileReadHandler` fornece o conteúdo ou a listagem em uma mensagem `user` separada somente à resposta atual. Não há tool calling, execução arbitrária, escrita, leitura automática de múltiplos arquivos, busca pelo conteúdo, registry ou manifesto genérico de capabilities; esses recursos continuam `planned` quando aplicável.

### Escopo concluído da Fase 3

Persistent Memory usa objetos com `id`, `content`, `source`, `created_at` e `updated_at` em JSON local. Repository e datasource permanecem separados; gravações são atômicas e falhas de persistência são explícitas. O usuário pode listar, buscar, criar, editar e excluir memórias por comandos literais ou por propostas naturais confirmadas, com proteção por ID e snapshot quando aplicável. A prevenção de duplicatas cobre equivalência textual superficial sem alterar o conteúdo persistido. Somente o conteúdo das memórias entra no contexto do modelo. O comportamento possui testes automatizados e a integração local foi validada ponta a ponta com Gemma 3 12B.

### Limitações e evoluções planejadas

- A prevenção atual reconhece equivalência textual, não equivalência de significado; equivalência semântica e detecção de contradições permanecem `planned`.
- Tipos de memória e `subjects` estruturados permanecem `planned`.
- Seleção por relevância, orçamento de contexto e compactação permanecem `planned`; atualmente todas as memórias são enviadas ao modelo.
- Temporalidade e captura automática configurável permanecem `planned`.
- JSON continua sendo o armazenamento implementado; SQLite será considerado somente quando houver necessidade concreta.
- Busca vetorial permanece `planned` e só deve ser adotada se uma necessidade de recuperação justificar sua complexidade.
- O datasource JSON usa cache por instância e assume um único writer durante a execução.

## Roadmap

| Fase | Nome | Objetivo | Status |
| --- | --- | --- | --- |
| 0 | Foundation | Setup, monorepo, documentação e qualidade | `implemented` |
| 1 | CLI and local conversation | CLI e primeira conversa com modelo local substituível | `implemented` |
| 2 | Session context | Histórico e contexto útil na sessão | `implemented` |
| 3 | Persistent memory | Memória local transparente e consultável | `implemented` |
| 4 | Tools and capabilities | Capabilities seguras e incrementais | `in_progress` |
| 5 | Knowledge and retrieval | Indexação de documentos, código e informações | `planned` |
| 6 | Desktop interaction | Recursos do computador com permissões e auditoria | `planned` |
| 7 | Vision | Captura e interpretação de tela e imagens | `planned` |
| 8 | Voice | Entrada e resposta por voz local | `planned` |
| 9 | Persistent presence | Experiência contínua, possivelmente com avatar | `planned` |

O roadmap expressa direção, não compromisso de implementação antecipada. Cada fase deve ser refinada quando se tornar o próximo incremento concreto.
