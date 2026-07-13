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

O pacote `packages/conversation` concentra a orquestração da conversa, o histórico da sessão e a construção de contexto, sem depender do CLI. O CLI permanece como adaptador de entrada e saída e converte texto em comandos tipados.

No CLI, `commands.py` define as intenções tipadas, `command_parser.py` converte texto nesses comandos e `handlers/memory.py` traduz comandos de memória em chamadas ao `MemoryService` e mensagens de saída. `app.py` mantém somente o loop, o despacho de alto nível e o composition root.

O contrato `ModelProvider` pertence a `packages/conversation`, que é seu consumidor. O pacote `packages/inference` contém o primeiro adaptador, que usa a API HTTP local do Ollama. llama.cpp, LM Studio e vLLM continuam alternativas futuras. Gemini, ChatGPT e outras IAs externas podem ajudar no desenvolvimento, mas não são dependências de runtime.

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

Capabilities futuras incluem filesystem, terminal, código, Flutter, browser/web, desktop, visão, voz, Git/GitHub e organização pessoal. Cada uma deve ter contratos, configuração, permissões e testes próprios apenas quando a complexidade justificar.

## Segurança

- Negar ou pedir confirmação quando o risco for significativo.
- Aplicar menor privilégio e restringir diretórios e comandos.
- Separar sugerir, planejar e executar.
- Registrar ações relevantes para auditoria.
- Confirmar ações sensíveis e nunca executar ações destrutivas silenciosamente.
- Proteger o sistema contra instruções maliciosas vindas de documentos, páginas e resultados externos.

## Componentes adiados

Event bus próprio, container de DI, service registry, runtime complexo, planner separado e múltiplos agentes autônomos só devem existir quando uma necessidade concreta os justificar.
