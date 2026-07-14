# Visão geral da arquitetura

## Princípios

1. **Conversation first:** conversa, raciocínio e relacionamento contínuo são o centro; automação é apoio.
2. **Local-first e offline-first:** núcleo, modelo principal, memória e configuração devem funcionar localmente.
3. **Provider agnostic:** o núcleo depende de contratos internos, não de providers concretos.
4. **Capabilities modulares:** habilidades adicionais possuem limites, permissões e testes próprios quando necessário.
5. **Security by default:** ações seguem menor privilégio, políticas explícitas, auditoria e confirmação.
6. **Memória transparente:** memórias são explicáveis, consultáveis, editáveis e removíveis.
7. **Implementação incremental:** pensar no longo prazo e implementar apenas o próximo incremento útil.
8. **Contratos em limites reais:** usar interfaces quando existe um limite arquitetural, sem abstrações prematuras.
9. **Controle dos dados:** históricos, configurações, índices e memórias pertencem ao usuário.
10. **Auditabilidade:** ações relevantes e decisões executáveis devem ser inspecionáveis.

## Fluxo conceitual

```text
Usuário
  ↓
Interface
  ↓
Conversation
  ↓
Contexto + Memória
  ↓
Raciocínio / Orquestração de modelo
  ↓
Conhecimento + Capabilities
  ↓
Resposta
```

O modelo é um componente usado pela conversa e pelo raciocínio, não o sistema inteiro. Nem toda solicitação precisa produzir plano ou executar ferramenta.

## Regras de dependência

- Apps dependem de contratos e pacotes internos durante os casos de uso. O entry point pode importar adaptadores concretos exclusivamente para compor o grafo de dependências.
- Conversation ou core não importa Ollama, Gemini, OpenAI ou outra API externa.
- Infraestrutura implementa contratos das camadas internas.
- Capabilities não importam detalhes internos umas das outras.
- Interfaces de usuário não contêm lógica de IA, memória ou ferramentas.
- Ações do sistema passam por política de segurança antes da execução.

O pacote `packages/conversation` concentra a orquestração da conversa, o histórico da sessão, a identidade mínima do Aska e a construção de mensagens estruturadas com papéis `system`, `user` e `assistant`, sem depender do CLI. O CLI permanece como adaptador de entrada e saída e converte texto em comandos tipados.

Os pedidos naturais de memória implementados neste estágio são a mudança do nome de Gustavo e a criação, edição ou exclusão explícita de uma memória. `packages/conversation` preserva padrões exatos como caminhos rápidos e usa gates locais separados para submeter somente paráfrases relacionadas a essas ações a um intérprete provider-agnostic baseado no modelo. Detectores determinísticos e intérprete produzem propostas tipadas (`NameUpdateIntent`, `AddMemoryIntent`, `EditMemoryIntent` ou `DeleteMemoryIntent`); propostas imutáveis mantêm confirmação e cancelamento locais. Para edição e exclusão, o CLI seleciona candidatas localmente sem enviar memórias ou IDs ao modelo, e `MemoryService` executa por ID e snapshot. Captura automática e ações genéricas continuam `planned`.

No CLI, `commands.py` define as intenções tipadas, `command_parser.py` converte texto nesses comandos e `handlers/memory.py` traduz comandos literais de memória em chamadas ao `MemoryService` e mensagens de saída. `NaturalMemoryHandler`, em `handlers/natural_memory.py`, mantém somente durante a sessão a proposta pendente e coordena detecção, interpretação, seleção, confirmação e apresentação dos fluxos naturais existentes. `app.py` mantém o loop, o despacho de alto nível e o composition root; o handler é uma coordenação específica do CLI, não um framework genérico de ações.

As primeiras capabilities implementadas são a leitura de um único arquivo textual conhecido e a listagem segura de caminhos de arquivos. Pedidos explícitos como `Leia docs/project/roadmap.md` extraem o caminho deterministicamente; um gate local limita o uso de `ModelFileIntentInterpreter` às variações naturais e aos pedidos de descoberta. O modelo produz somente uma intenção estruturada e não acessa arquivos nem decide permissões. `ReadTextFileCapability` lê um arquivo UTF-8 de até 64 KiB, enquanto `ListFilesCapability` enumera caminhos relativos com limites de profundidade e resultados, sem ler conteúdo e ignorando diretórios de infraestrutura configurados. Ambas resolvem caminhos dentro do workspace e impedem escapes por caminho absoluto, travessia ou symlink. O conteúdo do arquivo ou a listagem entra em uma mensagem `user` separada apenas na solicitação atual, identificada pela fonte e marcada como dado não confiável; não altera a identidade em `system` nem é copiada para o histórico da conversa.

O contrato `ModelProvider` pertence a `packages/conversation`, que é seu consumidor, e expõe somente `generate()` sobre uma sequência provider-agnostic de `ModelMessage`. A identidade do Aska compõe a primeira mensagem `system`; entradas e respostas preservam os papéis `user` e `assistant`. O pacote `packages/inference` contém o primeiro adaptador, que converte essas mensagens para a API HTTP do Ollama sem definir identidade ou contexto. `warm_up()` e `unload()` são comportamentos específicos de `OllamaProvider` e são coordenados pelo composition root do CLI; não fazem parte de um lifecycle abstrato de providers. Um contrato de lifecycle só deve ser introduzido quando mais providers apresentarem uma necessidade comum concreta. llama.cpp, LM Studio e vLLM continuam alternativas futuras. Gemini, ChatGPT e outras IAs externas podem ajudar no desenvolvimento, mas não são dependências de runtime.

## Monorepo

```text
aska/
├── apps/
│   └── cli/
├── packages/
├── capabilities/
├── docs/
├── scripts/
├── tests/
├── data/
├── pyproject.toml
└── README.md
```

- `apps/`: interfaces executáveis, inicialmente o CLI.
- `packages/`: features e limites internos compartilhados, atualmente conversa, memória e inferência.
- `capabilities/`: funcionalidades independentes.
- `docs/`: arquitetura, decisões, roadmap e pesquisa.
- `scripts/`: desenvolvimento e manutenção.
- `tests/`: testes compartilhados e de integração.
- `data/`: memória, logs, cache, índices e modelos locais.

Não criar muitas pastas, classes ou módulos vazios. Uma abstração entra quando resolve uma responsabilidade real.

Cada package expõe sua API pública por `__init__.py`, de forma semelhante a um barrel file em Dart. Apps e outras features usam essa API pública; módulos dentro da própria feature importam diretamente seus contratos e modelos para preservar a direção das dependências.

## Capabilities

A leitura textual confinada ao workspace e a listagem segura de caminhos de arquivos estão `implemented`. A listagem somente descobre caminhos: leitura automática de múltiplos arquivos, busca pelo conteúdo e escrita continuam `planned`. Terminal, código, Flutter, browser/web, desktop, visão, voz, Git/GitHub e organização pessoal também permanecem `planned`. Cada operação adicional deve ter contratos, configuração, permissões e testes próprios apenas quando uma necessidade concreta justificar.

## Segurança

- Negar ou pedir confirmação quando o risco for significativo.
- Aplicar menor privilégio e restringir diretórios e comandos.
- Resolver e validar caminhos localmente contra o workspace permitido antes de acessar o filesystem.
- Separar sugerir, planejar e executar.
- Registrar ações relevantes para auditoria.
- Confirmar ações sensíveis e nunca executar ações destrutivas silenciosamente.
- Proteger o sistema contra instruções maliciosas vindas de documentos, páginas e resultados externos.

## Componentes adiados

Event bus próprio, container de DI, service registry, runtime complexo, planner separado e múltiplos agentes autônomos só devem existir quando uma necessidade concreta os justificar.
