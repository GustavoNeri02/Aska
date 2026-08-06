# Estado e roadmap

## Estado atual

**Fase atual:** Tools and capabilities está `in_progress`; além do filesystem read-only, a primeira ação externa controlada abre uma pasta do workspace no Explorador somente após confirmação local.

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
- Consultas naturais sobre documentos conhecidos e pedidos explícitos de localização de arquivos usam o fluxo read-only confinado ao workspace; buscas sem resultado encerram localmente sem chamar o modelo.
- O checkup manual de consultas a documentos conhecidos, localização explícita e buscas vazias foi concluído com sucesso.
- Busca textual literal dentro de arquivos está `implemented` com intenção e handler próprios, resultados tipados por caminho e linha, limites locais e contexto temporário; seu checkup manual foi concluído com sucesso.
- Sugestões aproximadas para localizações explícitas por nome estão `implemented` com mesma extensão, normalização local, corte conservador e sem leitura ou seleção automática; seu checkup manual ainda está pendente.
- Abertura de uma pasta do workspace no Explorador do Windows está `implemented` como primeira ação externa controlada: intenção limitada, proposta com alvo exato, confirmação local, revalidação por snapshot e launcher injetável. O checkup manual ainda está pendente.
- A decisão conversacional única está `implemented` com envelope JSON estrito de `reply` ou `capability_proposal`, catálogo fechado e o mesmo contexto de identidade, memórias e histórico. Frases exatas são somente fast paths; paráfrases podem gerar `OpenWorkspaceLocationProposal`, enquanto políticas e execução permanecem locais.
- A execução confirmada da suíte inteira de testes está `implemented` como action sem parâmetros controlados pelo modelo. O comando fixo é `python -m pytest -q`, com workspace revalidado, `shell=False`, timeout, saída limitada e resultado real tipado. Subconjuntos não são ampliados para a suíte inteira; alternativas usam `offer` tipada, e execução ou cancelamento geram evento autoritativo apresentado pela IA e preservado para follow-ups. O checkup manual desta correção está pendente.
- A separação de voz está `implemented` no CLI de produção: handlers de memória, filesystem, busca, desktop e terminal emitem fatos rotulados como `Sistema`; um `ConversationEvent` agrupado gera a fala natural da `Aska`. Lifecycle, controles de confirmação e fallback sem provider permanecem determinísticos. O checkup manual está pendente.

### Comportamento atual

- Session Context está implementado e usa histórico em memória com papéis `user` e `assistant` durante a conversa atual; a identidade mínima do Aska é enviada como mensagem `system`.
- A orquestração de conversa e a construção de contexto estão separadas do CLI; entradas do terminal são convertidas em comandos tipados antes da execução.
- Persistent Memory está `implemented` com persistência JSON estruturada, identidade e metadados mínimos, registro explícito por `lembrar:`, remoção explícita por `esquecer:`, edição explícita por `editar memória:`, pesquisa textual por `buscar memória:` e listagem por `memórias`.
- O fluxo natural está implementado para alteração do nome e criação, edição ou exclusão explícita de uma memória. Padrões exatos evitam chamadas ao modelo quando disponíveis e gates separados limitam a interpretação de paráfrases; o modelo apenas propõe, enquanto seleção, confirmação e persistência permanecem locais. Captura automática e pedidos genéricos mais amplos continuam `planned`.
- O comportamento atual do CLI não depende mais da resposta placeholder da Sprint 1.
- As capabilities de filesystem leem um único arquivo UTF-8 conhecido de até 64 KiB ou listam caminhos com profundidade e quantidade limitadas dentro de `ASKA_WORKSPACE_ROOT`; conteúdo e listagens não entram no histórico e são tratados como dados não confiáveis.

### Incremento atual da Fase 4

O recorte read-only atual de Tools and capabilities está `implemented`: `ReadTextFileCapability` lê um arquivo textual conhecido, `ListFilesCapability` descobre caminhos relativos sem ler conteúdo e `SearchTextCapability` procura texto literal dentro de arquivos elegíveis. Todas aplicam confinamento local ao workspace e retornam resultados tipados; listagem e busca limitam profundidade e quantidade. Consultas naturais sobre documentos conhecidos, localização explícita e sugestão aproximada conservadora de nomes estão `implemented`. Quando um pedido de leitura informa somente o nome de um arquivo ausente na raiz, `NaturalFileReadHandler` usa a listagem segura para resolver uma única correspondência exata ou solicita o caminho relativo diante de ambiguidade. Uma localização nominal vazia pode apresentar sugestões locais com a mesma extensão, sem ler ou selecionar arquivos; listagens e buscas sem correspondência produzem resposta local e não chamam o provider conversacional. Conteúdo, listagem ou correspondências não vazias são fornecidos em uma mensagem `user` separada somente à resposta atual. Os checkups manuais de leitura, descoberta e busca textual foram concluídos; o checkup manual das sugestões aproximadas permanece pendente. Não há tool calling, execução arbitrária, escrita, leitura automática de múltiplos arquivos como contexto integral, busca semântica, regex, indexação persistente, registry ou manifesto genérico de capabilities; esses recursos continuam `planned` quando aplicável.

O primeiro recorte executável também está `implemented`: abrir uma pasta existente do workspace no Explorador do Windows. Após os fluxos especializados anteriores, `ConversationService.decide()` faz um único round trip contextual e retorna `reply` ou uma proposal do catálogo fechado. Para `open_workspace_location`, o modelo pode interpretar paráfrases usando histórico e memórias; confinamento, proposta, confirmação, snapshot e revalidação são locais. Detectores de frases exatas existem somente como fast paths. Esse recorte não permite escolher executáveis, passar argumentos livres, abrir arquivos, usar shell, controlar mouse ou teclado nem executar comandos. A interação desktop geral da Fase 6 continua `planned`; o checkup manual desta operação está pendente.

O segundo recorte executável também está `implemented`: `run_project_tests` executa apenas a suíte inteira por `python -m pytest -q` na raiz do workspace. A proposal não contém parâmetros; comando, cwd, timeout e limite de saída pertencem à capability local e são exibidos antes da confirmação. Pedidos por primeiro teste, arquivo, nome ou opção não podem gerar essa proposal; a suíte completa pode ser oferecida por estado tipado e aceita em linguagem natural no turno seguinte. O runner captura stdout, stderr e exit code sem shell. Resultado e cancelamento viram eventos estruturados: os fatos brutos continuam locais, a IA gera a apresentação conversacional, e ambos permanecem disponíveis ao próximo turno. Essa operação executa código do workspace, portanto não é classificada como read-only apesar de não oferecer escrita ou comando arbitrário. Ruff, build, subconjuntos, argumentos livres, seleção de comandos e terminal geral continuam `planned`; o checkup manual desta correção está pendente.

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
