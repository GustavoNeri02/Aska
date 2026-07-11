# Documentação do Aska

Esta pasta é a fonte de verdade do projeto. Cada assunto possui um documento autoritativo para evitar divergência e manutenção duplicada.

## Índice

- [Visão do produto](product/vision.md): identidade, objetivos, escopo e experiência desejada.
- [Arquitetura](architecture/overview.md): princípios, componentes, dependências, providers, capabilities e segurança.
- [Sistema de memória](architecture/memory.md): tipos, captura, persistência e controles do usuário.
- [Guia de desenvolvimento](development/guide.md): stack, padrões, processo, testes e ferramentas.
- [Estado e roadmap](project/roadmap.md): implementação atual, Sprint e evolução planejada.
- [Registro de decisões](project/decisions.md): decisões vigentes, abertas, adiadas e substituídas.

## Precedência

Quando houver conflito, use esta ordem:

1. decisão mais recente registrada em `project/decisions.md`;
2. documento temático responsável pelo assunto;
3. resumo do `README.md` na raiz;
4. referências históricas.

Conversas, exemplos e comentários antigos não substituem uma decisão documentada. Ao mudar arquitetura, responsabilidades, contratos ou dependências, atualize o documento temático e registre a decisão quando ela tiver impacto duradouro.

## Estados

- `planned`: definido, mas ainda não iniciado;
- `in_progress`: em desenvolvimento;
- `implemented`: presente e verificável no código;
- `superseded`: substituído por uma decisão posterior;
- `rejected`: considerado e descartado.

Não apresente comportamento planejado como implementado.
