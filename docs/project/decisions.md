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

- Primeiro runtime local: Ollama, llama.cpp ou LM Studio.
- Primeiro modelo local adequado ao hardware e ao objetivo.
- Contrato de mensagens e provider.
- Persistência inicial da memória: JSON, SQLite ou alternativa simples.
- Momento de separar `packages/conversation` e `packages/models`.
- Formato do manifesto de capabilities.
- Primeira capability concreta, provavelmente filesystem.
- Tecnologia da interface desktop futura.
- Estratégia futura de voz, visão e avatar.

## Regra de atualização

Uma decisão nova deve registrar contexto, escolha, motivo e estado. Quando substituir outra, a anterior permanece resumida e marcada como `superseded`. Mudanças arquiteturais também devem atualizar o documento temático correspondente.
