# Instruções de desenvolvimento — Aska

## Antes de trabalhar

1. Leia o índice em [`docs/README.md`](docs/README.md) e os documentos relacionados à tarefa.
2. Inspecione o código e o estado do Git antes de sugerir arquitetura ou alterar arquivos.
3. Diferencie explicitamente o que está `planned`, `in_progress`, `implemented`, `superseded` ou `rejected`.
4. Não invente arquivos, funcionalidades, comandos executados ou estado do repositório.
5. Quando houver conflito, siga a precedência documental registrada em `docs/README.md`.

## Sobre o desenvolvedor

Gustavo é desenvolvedor profissional de Flutter e Dart, com experiência em arquitetura modular, monorepos, Clean Architecture, injeção de dependência, gerenciamento de estado e testes automatizados. Este é seu primeiro projeto sério em Python.

Não o trate como iniciante em programação. Ao apresentar conceitos específicos de Python, compare com Dart ou Flutter quando isso ajudar, especialmente para:

- `pyproject.toml` e `pubspec.yaml`;
- módulos, pacotes e imports;
- ambientes virtuais e isolamento de dependências;
- `Protocol` e contratos/interfaces;
- `dataclass` e modelos simples de dados;
- Pytest e testes do Flutter.

Responda normalmente em português do Brasil, apresente primeiro a ação prática, explique trade-offs e discorde quando uma decisão prejudicar o projeto.

## Regras de colaboração

- Preserve a arquitetura documentada e atualize o documento responsável quando uma decisão mudar.
- Prefira mudanças pequenas, revisáveis, executáveis e cobertas por testes proporcionais.
- Não adicione dependências sem explicar qual problema concreto resolvem.
- Não introduza abstrações, frameworks ou módulos vazios antecipadamente.
- Mantenha pontos de entrada pequenos e injete dependências por parâmetros enquanto isso for suficiente.
- Evite estado global, singletons e refatorações não relacionadas.
- Não execute ações destrutivas silenciosamente.
- Não trate ideias futuras como funcionalidades existentes.

## Referências

- [Visão do produto](docs/product/vision.md)
- [Arquitetura](docs/architecture/overview.md)
- [Sistema de memória](docs/architecture/memory.md)
- [Guia de desenvolvimento](docs/development/guide.md)
- [Estado e roadmap](docs/project/roadmap.md)
- [Registro de decisões](docs/project/decisions.md)

O Aska deve ser projetado para crescer, mas implementado incrementalmente: conversa, contexto e memória são o núcleo; ferramentas e automação são capabilities auxiliares.
