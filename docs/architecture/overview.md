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

O pacote `packages/conversation` concentra a orquestração da conversa, o histórico da sessão, a identidade mínima do Aska, a recuperação lexical seletiva de memórias e a construção de mensagens estruturadas com papéis `system`, `user` e `assistant`, sem depender do CLI. O CLI permanece como adaptador de entrada e saída e converte texto em comandos tipados. A recuperação compõe o contrato de leitura existente sem alterar persistência ou CRUD: seleciona no máximo cinco memórias por correspondência exata, plural simples ou radical longo conservador com a mensagem atual e até dois turnos recentes. A conversa mantém a última seleção explicável apenas para transparência no turno seguinte.

Os pedidos naturais de memória implementados neste estágio são a mudança do nome de Gustavo e a criação, edição ou exclusão explícita de uma memória. `packages/conversation` preserva padrões exatos como caminhos rápidos e usa gates locais separados para submeter somente paráfrases relacionadas a essas ações a um intérprete provider-agnostic baseado no modelo. Detectores determinísticos e intérprete produzem propostas tipadas (`NameUpdateIntent`, `AddMemoryIntent`, `EditMemoryIntent` ou `DeleteMemoryIntent`); propostas imutáveis mantêm confirmação e cancelamento locais. Para edição e exclusão, o CLI seleciona candidatas localmente sem enviar memórias ou IDs ao modelo, e `MemoryService` executa por ID e snapshot. Captura automática e ações genéricas continuam `planned`.

No CLI, `commands.py` define as intenções tipadas, `command_parser.py` converte texto nesses comandos e `handlers/memory.py` traduz comandos literais de memória em chamadas ao `MemoryService`. `NaturalMemoryHandler`, em `handlers/natural_memory.py`, mantém somente durante a sessão a proposta pendente e coordena os fluxos naturais existentes. `app.py` é o composition root e coordena configuração e lifecycle. `conversation_loop.py` contém o loop de entrada e a `CliSession`, que roteia uma sessão já composta e apresenta seus resultados. `CliActionCoordinator` concentra apenas a precedência, o cancelamento e o despacho fechado de desktop, testes e lint com campos explícitos; nenhum desses componentes é um registry ou framework genérico de ações.

A primeira ação externa controlada abre uma pasta já existente do workspace no Explorador de Arquivos do Windows. `ConversationService.decide()` usa o mesmo contexto provider-agnostic da conversa — identidade, memórias e histórico — e solicita um envelope JSON estrito que contém `reply` ou `capability_proposal`. O catálogo implementado contém `OpenWorkspaceLocationProposal`, `RunProjectTestsProposal` e `RunProjectLintProposal`. Texto livre não vazio pode ser degradado com segurança para `ReplyDecision`, evitando que conversa casual falhe por formatação; somente uma proposal JSON tipada pode sugerir ação. Assim, o mesmo round trip pode responder normalmente ou compreender uma paráfrase e sugerir uma action estruturada; o modelo não executa, concede permissões nem informa sucesso. Detectores exatos permanecem apenas como fast paths opcionais, não como vocabulário necessário para acionar a capability.

Quando existe uma proposta pendente, toda resposta textual do usuário passa por `ModelConfirmationInterpreter`, que produz somente `confirm`, `cancel` ou `unknown` em JSON estrito e entende linguagem natural, variações e outros idiomas. Essa classificação não autoriza efeitos por si só: o handler mantém a proposta tipada, trata `unknown` como recusa segura de execução e somente o código local revalida e executa a ação. O parser determinístico permanece apenas como fallback injetável para testes e ambientes sem o intérprete composto; o CLI de produção sempre injeta o intérprete baseado no provider.

`NaturalOpenLocationHandler` entrega a proposal à capability, que resolve e confina o caminho localmente, registra um snapshot do diretório e só entrega esse alvo a um `LocationLauncher` injetado depois de confirmação explícita no CLI. Antes da execução, o alvo é validado novamente e uma troca invalida a proposta. O adaptador Windows usa o caminho absoluto de `explorer.exe`, argumentos separados e `shell=False`. A confirmação textual comum foi extraída para o CLI porque memória e desktop agora são consumidores reais; proposals e efeitos continuam em handlers específicos. O envelope não é um registry dinâmico, planner ou executor genérico: novas actions exigem proposal, parsing estrito, handler, política e testes explícitos. Somente `reply` entra automaticamente no histórico; uma proposal não é registrada como execução concluída.

A segunda ação externa controlada executa a suíte inteira de testes do projeto. O catálogo expõe `RunProjectTestsProposal` sem campos: o modelo não fornece subconjunto, arquivo, nome de teste, comando, argumentos, diretório ou timeout. Pedidos por execução parcial devem receber uma resposta sobre a limitação, nunca ser ampliados silenciosamente para a suíte inteira. Uma `ReplyDecision` pode carregar uma `offer` tipada quando a Aska oferece a suíte completa como alternativa; o `ConversationService` mantém essa oferta separada do texto para que o turno seguinte possa aceitá-la naturalmente sem depender de uma frase cadastrada.

`RunProjectTestsCapability` possui a operação fixa `python -m pytest -q`, usa exclusivamente a raiz resolvida do workspace, registra um snapshot do diretório antes da confirmação e limita tempo e saída apresentada. `PythonProjectTestRunner` resolve o interpretador do ambiente atual e chama `subprocess.run()` com argv separado, `shell=False`, captura de stdout e stderr e timeout. O resultado tipado diferencia sucesso, testes falhos, timeout, falha ao iniciar e mudança do workspace. Proposta, execução e cancelamento criam fatos locais autoritativos; uma chamada contextual separada permite que a IA os apresente naturalmente sem mencionar o protocolo interno. Para resultados executáveis, a resposta deve reconhecer no envelope exatamente o status local, impedindo que uma fala contraditória seja aceita no histórico. A fala gerada e o evento estruturado permanecem associados no histórico para follow-ups, enquanto resultados extensos preservam início e fim dentro de limite próprio. Comando, diretório, timeout, proposta pendente e confirmação continuam definidos e validados deterministicamente, embora sua apresentação visível pertença à Aska. Rodar testes executa código do próprio workspace e, portanto, sempre exige proposta explícita e confirmação local.

Testes e lint compartilham somente `FixedWorkspaceTarget` e as funções de validação, snapshot, revalidação e truncamento em `capabilities/terminal/process.py`. Comandos, statuses, resultados e políticas permanecem nas capabilities específicas. Desktop não usa essa infraestrutura: resolução de caminho, snapshot de diretório e launcher formam um limite de efeito diferente.

No CLI composto para produção, handlers retornam `HandlerResult` com domínio, tipo, fatos estruturados e contexto documental opcional. Eles não conhecem `output_writer`, terminal ou `ConversationService` e não produzem frases para o usuário. O loop central converte o resultado em `ConversationEvent` ou contexto temporário; `ConversationService` usa o modelo para produzir a única fala visível, atribuída a `Aska`. Eventos sensíveis exigem que a resposta reconheça estruturalmente domínio e tipo antes de sua fala ser aceita; confirmações não podem ser apresentadas como ações já concluídas. Somente a borda do app imprime essa fala. Lifecycle não produz uma segunda voz. Falhas que impedem o próprio modelo de responder — como provider indisponível, workspace inválido ou envelope irrecuperável — aparecem como `Erro`, nunca como Aska.

As primeiras capabilities implementadas são leitura textual, listagem de caminhos e busca textual literal, todas read-only e confinadas ao workspace. Pedidos diretos para ler, resumir, mostrar ou retornar um arquivo com caminho explícito extraem esse caminho deterministicamente. Perguntas de conteúdo que referenciam inequivocamente `README`, `AGENTS`, `roadmap` ou o documento de decisões também produzem uma intenção determinística; perguntas genéricas sobre documentos ou sobre como escrever um README não acionam filesystem. Pedidos de localização com nome de arquivo explícito também são detectados deterministicamente; demais pedidos que combinam uma expressão clara de localização com referência a arquivo ou documento passam pelo gate de descoberta estruturada, sem leitura de conteúdo. Um gate local limita o uso de `ModelFileIntentInterpreter` às demais variações naturais e aos pedidos de descoberta. Quando o usuário informa somente o nome e ele não existe na raiz, o CLI procura correspondências exatas pela listagem segura: uma correspondência única é lida, enquanto múltiplas ou uma busca truncada exigem que o usuário escolha um caminho relativo. Listagens sem resultados são encerradas pelo handler sem criar contexto de arquivo; o resultado tipado é apresentado pela IA como qualquer outro evento local. O modelo não seleciona arquivos, não acessa o filesystem e não decide permissões.

`SearchTextCapability` coordena `ListFilesCapability` e `ReadTextFileCapability` sem duplicar as políticas de path e leitura. Ela realiza comparação literal sem distinção de caixa em arquivos UTF-8 de até 64 KiB, com limites padrão de profundidade 4, 200 arquivos, 50 correspondências, query de 256 caracteres e trecho de 240 caracteres. Diretório e extensão podem restringir o escopo; binários, arquivos grandes, vazios ou não UTF-8 são ignorados. Cada resultado contém caminho relativo, número da linha e trecho. A intenção e a coordenação do CLI ficam respectivamente em `natural_search.py` de conversation e handlers, separadas do fluxo de leitura/listagem. Termos entre aspas usam caminho determinístico; paráfrases passam por gate próprio e JSON estrito. Zero ocorrências encerra a busca no handler e produz um evento local para apresentação pela IA; resultados não vazios entram em uma mensagem `user` temporária marcada como dado não confiável. Busca semântica, regex, indexação persistente e substituição continuam `planned`.

Descrições explícitas do arquivo local de memórias são resolvidas deterministicamente como descoberta de `memories.json`, sem entregar ao modelo a escolha de caminho. Quando uma localização explícita por nome e extensão não encontra correspondência exata, o handler pode sugerir caminhos semelhantes já enumerados com segurança. `name_matcher.py` é um componente puro: normaliza caixa e acentos, exige a mesma extensão, considera plurais simples em `s` e `ies`, calcula similaridade com `difflib.SequenceMatcher`, aplica corte conservador e limita sugestões. O matcher não acessa o filesystem, não lê arquivos e não escolhe uma sugestão; o CLI não permite que o modelo escolha uma candidata, mas envia o resultado tipado ao provider somente para apresentação natural. Caminhos completos, nomes sem extensão e pedidos sem referência nominal não usam aproximação.

`ReadTextFileCapability` lê um arquivo UTF-8 de até 64 KiB, enquanto `ListFilesCapability` enumera caminhos relativos com limites de profundidade e resultados, sem ler conteúdo, ignorando diretórios de infraestrutura configurados e pulando subárvores inacessíveis; uma falha de acesso à própria raiz solicitada permanece explícita. As três capabilities resolvem caminhos dentro do workspace e impedem escapes por caminho absoluto, travessia ou symlink. Conteúdo, listagens e resultados entram somente na solicitação atual, não alteram a identidade em `system` nem são copiados para o histórico da conversa.

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

A leitura textual confinada ao workspace, a listagem segura de caminhos, sugestões aproximadas locais, a busca textual literal limitada, a abertura confirmada de uma pasta no Explorador e as operações fixas confirmadas de testes e lint estão `implemented`. Leitura automática de múltiplos arquivos como contexto integral, busca semântica, indexação persistente e escrita continuam `planned`. Terminal arbitrário, código, Flutter, browser/web, interação desktop geral, visão, voz, Git/GitHub e organização pessoal também permanecem `planned`. Cada operação adicional deve ter contratos, configuração, permissões e testes próprios apenas quando uma necessidade concreta justificar.

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

Respostas comuns e proposals usam um único round trip quando a capability desktop está composta. Fluxos especializados anteriores, como memória e filesystem, continuam com seus handlers atuais e poderão migrar para o envelope somente quando isso preservar suas garantias locais e reduzir complexidade real.
