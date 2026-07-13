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

### Memória persistente local explícita — `in_progress`

A primeira forma de memória persistente continua sendo o armazenamento local em JSON, exclusivamente com objetos contendo identidade estável, conteúdo, origem e datas de criação e alteração em UTC. Listas de strings não são suportadas. Os comandos explícitos do CLI permanecem responsáveis pela captura e controle, e somente o conteúdo é enviado ao modelo por padrão. SQLite é uma evolução provável quando o armazenamento simples deixar de atender, mas não foi adotado neste incremento.

O domínio e as regras de memória são separados da persistência por `MemoryService` e `MemoryRepository`. `LocalMemoryRepository` implementa o contrato e depende de `MemoryLocalDataSource`; `JsonMemoryDataSource` é a implementação atual, responsável por JSON, filesystem, cache lazy e escrita atômica. Essa separação foi adotada para permitir um futuro `SqliteMemoryDataSource` sem alterar os casos de aplicação. SQLite permanece `planned` e não foi implementado.

### Conversa independente da interface — `implemented`

Histórico da sessão, composição de contexto e chamada ao modelo pertencem a `packages/conversation`. O CLI interpreta entradas em comandos tipados e apresenta resultados. A composição de `OllamaProvider`, `JsonMemoryDataSource`, `LocalMemoryRepository` e `MemoryService` continua manual no entry point, sem container de injeção de dependência.

### Provider como port da conversa — `implemented`

O contrato `ModelProvider` pertence a `packages/conversation`, camada que o consome, e permanece restrito a `generate()`. O adaptador Ollama fica em `packages/inference`; seu `warm_up()` e `unload()` são coordenados concretamente pelo composition root do CLI e não constituem um lifecycle abstrato de providers. Esse contrato só será ampliado quando existir necessidade comum entre providers. O nome anterior `packages/models` foi substituído por ser ambíguo com modelos de domínio.

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
- Primeira capability concreta, provavelmente filesystem.
- Tecnologia da interface desktop futura.
- Estratégia futura de voz, visão e avatar.

## Regra de atualização

Uma decisão nova deve registrar contexto, escolha, motivo e estado. Quando substituir outra, a anterior permanece resumida e marcada como `superseded`. Mudanças arquiteturais também devem atualizar o documento temático correspondente.
