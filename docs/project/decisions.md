# Registro de decisões

## Decisões vigentes

### Conversa como núcleo — `implemented`

Conversa, raciocínio, contexto e memória definem o produto. Automação, controle do computador, visão e voz são capabilities auxiliares.

### Local-first e provider agnostic — `implemented`

O núcleo deve funcionar localmente e depender de contratos internos. Gemini, ChatGPT e outros serviços externos são ferramentas opcionais de desenvolvimento, não dependências do produto.

### CLI antes de interface desktop — `implemented`

A primeira interface é o terminal dentro da IDE. A tecnologia de desktop permanece aberta.

### Implementação incremental — `implemented`

Abstrações e módulos entram apenas para resolver necessidades reais. O projeto não criará antecipadamente uma arquitetura extensa de kernel, planner, ferramentas ou agentes.

### Markdown como fonte documental — `implemented`

Documentos temáticos em Markdown são a fonte de verdade. O espelho JSON foi removido porque não possuía consumidor e criava risco de divergência.

### Ollama como primeiro provider local — `implemented`

O primeiro adaptador usa a API HTTP local do Ollama atrás do contrato `ModelProvider`. A integração utiliza a biblioteca padrão do Python, sem SDK ou dependência de runtime, e não impede adaptadores futuros.

### Gemma 3 12B como primeiro modelo local — `implemented`

O modelo padrão é `gemma3:12b`, adequado à GPU principal com 16 GB de VRAM. A escolha permanece configurável por `ASKA_MODEL` e não faz parte do contrato interno.

### Memória persistente local explícita — `implemented`

A primeira forma de memória persistente é o armazenamento local em JSON, exclusivamente com objetos contendo identidade estável, conteúdo, origem e datas de criação e alteração em UTC. Listas de strings não são suportadas. A captura ocorre por comando literal ou por proposta natural explícita confirmada; os comandos do CLI permanecem disponíveis para controle, e somente o conteúdo é enviado ao modelo por padrão. A prevenção de duplicatas cobre equivalência textual superficial, não equivalência semântica ou contradições. SQLite poderá ser considerado quando o armazenamento simples deixar de atender, mas não foi adotado nesta fase.

O domínio e as regras de memória são separados da persistência por `MemoryService` e `MemoryRepository`. `LocalMemoryRepository` implementa o contrato e depende de `MemoryLocalDataSource`; `JsonMemoryDataSource` é a implementação atual, responsável por JSON, filesystem, cache lazy e escrita atômica. Essa separação foi adotada para permitir um futuro `SqliteMemoryDataSource` sem alterar os casos de aplicação. SQLite permanece `planned` e não foi implementado.

### Conversa independente da interface — `implemented`

Histórico da sessão, composição de contexto e chamada ao modelo pertencem a `packages/conversation`. No CLI, `app.py` mantém o loop, o despacho de alto nível e o composition root, enquanto `NaturalMemoryHandler` coordena os fluxos naturais específicos da interface. A composição de `OllamaProvider`, `JsonMemoryDataSource`, `LocalMemoryRepository` e `MemoryService` continua manual no entry point, sem container de injeção de dependência.

### Provider como port da conversa — `implemented`

O contrato `ModelProvider` pertence a `packages/conversation`, camada que o consome, e permanece restrito a `generate()`, agora recebendo uma sequência de mensagens estruturadas provider-agnostic. O adaptador Ollama fica em `packages/inference` e apenas converte papéis e conteúdos para seu payload; seu `warm_up()` e `unload()` são coordenados concretamente pelo composition root do CLI e não constituem um lifecycle abstrato de providers. Esse contrato só será ampliado quando existir necessidade comum entre providers. O nome anterior `packages/models` foi substituído por ser ambíguo com modelos de domínio.

### Identidade mínima e mensagens estruturadas — `implemented`

A identidade estável do Aska pertence a `packages/conversation` e é enviada como mensagem `system`, independentemente do modelo configurado. Mensagens de Gustavo e respostas da Aska preservam respectivamente os papéis `user` e `assistant`; memórias fornecem apenas contexto textual na mensagem de sistema, sem expor identidade ou metadados persistidos. Neste incremento não existe sistema genérico de personas, prompts ou templates.

### Edição natural confirmada de nome — `implemented`

O primeiro pedido natural de gerenciamento de memória reconhece somente mudança do nome de Gustavo. Dois padrões explícitos formam o caminho rápido; um gate local encaminha apenas paráfrases relacionadas a nome para um intérprete provider-agnostic, que aceita JSON estrito e devolve somente uma proposta tipada. O modelo não recebe IDs nem executa ações. A proposta exige exatamente uma memória candidata e confirmação local, e é executada por `MemoryService` usando ID estável e snapshot. Os comandos literais permanecem como fallback, o fluxo poderá ser reutilizado por voz e pedidos naturais mais amplos continuam `planned`.

### Criação natural explícita de memória — `implemented`

Pedidos explícitos nos padrões completos `lembre que`, `memorize que`, `guarde que` ou `não esqueça que` produzem `AddMemoryIntent` deterministicamente, preservando o conteúdo informado e sem chamar o modelo. Paráfrases passam por um gate local e podem produzir a mesma intenção por JSON estrito. O modelo apenas interpreta e propõe uma única memória: não recebe serviços ou IDs, não persiste e não informa sucesso. A proposta imutável exige confirmação local e somente então o CLI chama `MemoryService.add()`, apresentando seu resultado real. Captura automática e frameworks de ações continuam `planned`.

### Exclusão natural confirmada de memória — `implemented`

Pedidos explícitos de exclusão usam padrões determinísticos ou um gate local específico seguido de `DeleteMemoryIntent` por JSON estrito. O modelo fornece somente a query e nunca recebe IDs, serviços ou a lista de memórias. O CLI seleciona candidatas localmente, priorizando igualdade sem distinção de caixa e usando pesquisa textual apenas quando não há igualdade; zero ou múltiplas candidatas não são escolhidas. A proposta guarda ID e snapshot, exige confirmação e é executada por `MemoryService.delete_by_id()`, que impede exclusão após conflito. Captura automática e frameworks de ações continuam `planned`.

### Edição natural genérica confirmada — `implemented`

Pedidos explícitos de alteração de uma memória ou informação passam por gate próprio e podem produzir `EditMemoryIntent` com query e novo conteúdo por JSON estrito. A precedência permanece nome, exclusão, edição genérica e inclusão. O modelo apenas interpreta a mensagem original e não recebe IDs ou memórias. `NaturalMemoryHandler` seleciona localmente uma única candidata por igualdade antes da pesquisa parcial, reutiliza `PendingMemoryEdit` e somente após confirmação chama `MemoryService.edit_by_id()`, preservando ID, snapshot, conflito, duplicidade e datas do domínio. Captura automática e frameworks genéricos de ações continuam `planned`.

### Leitura textual confinada ao workspace — `implemented`

A primeira capability permite ler um único arquivo textual UTF-8 de até 64 KiB dentro de um workspace explicitamente configurado e resolvido no composition root por `ASKA_WORKSPACE_ROOT`, usando o diretório atual como padrão. Um gate local evita interpretação adicional em mensagens comuns; quando acionado, `ModelFileIntentInterpreter` aceita somente JSON estrito com uma ação `read_text_file` e um caminho. O modelo não recebe conteúdo prévio, não acessa o filesystem e não concede permissões.

`ReadTextFileCapability`, em `capabilities/filesystem`, retorna resultados tipados e resolve o caminho localmente, rejeitando `file://`, caminhos absolutos POSIX ou Windows, travessia, symlinks que escapem do workspace, diretórios, arquivos ausentes, vazios, binários, não UTF-8 ou acima do limite. `NaturalFileReadHandler` coordena esse fluxo específico no CLI e entrega o resultado a `ConversationService` em uma mensagem `user` temporária marcada como dado não confiável; o conteúdo não altera a identidade em `system` nem entra no histórico. Não foi criado registry, manifesto, planner, tool calling ou abstração genérica de capabilities.

## Decisões substituídas, rejeitadas ou adiadas

- Automação como núcleo — `superseded` por conversa e IA pessoal como núcleo.
- Nome Atlas — `superseded` por Aska.
- Gemini Pro como modelo do produto — `rejected`; serviços externos não são runtime obrigatório.
- Arquitetura inicial centrada em Core, Planner, Tools e agentes autônomos — `superseded` pela evolução incremental orientada à conversa.
- Kernel, runtime complexo, DI, event bus e service registry na primeira Sprint — `superseded`; introduzir somente por necessidade concreta.
- FastAPI, Pydantic e SQLite como stack obrigatória inicial — `rejected`; podem ser reconsiderados quando houver um problema correspondente.
- Frameworks grandes de agentes no início — `rejected`.
- Banco vetorial antecipado — `rejected`.
- Documento extenso antes de qualquer código — `rejected` no estágio atual.
- Flutter Desktop já decidido — `rejected`; apenas a necessidade futura de uma interface desktop está reconhecida.
- Ferramentas iniciais predefinidas (`read_file`, `write_file`, terminal, busca de código, abertura de apps e screenshot) — `superseded`; capabilities serão priorizadas conforme casos reais e políticas de segurança.
- Múltiplos agentes autônomos — `planned` apenas como possibilidade distante, sem compromisso atual.

## Decisões abertas

- Critérios concretos para migrar a persistência de memória de JSON para SQLite.
- Formato do manifesto de capabilities.
- Tecnologia da interface desktop futura.
- Estratégia futura de voz, visão e avatar.

## Regra de atualização

Uma decisão nova deve registrar contexto, escolha, motivo e estado. Quando substituir outra, a anterior permanece resumida e marcada como `superseded`. Mudanças arquiteturais também devem atualizar o documento temático correspondente.
