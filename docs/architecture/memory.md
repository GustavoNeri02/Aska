# Sistema de memória

## Objetivo

Permitir continuidade e aprendizado útil sobre Gustavo sem armazenar tudo indiscriminadamente nem criar uma caixa-preta. Memórias, históricos, índices e configurações permanecem locais sempre que possível.

## Tipos previstos

- **Working:** contexto imediato da interação; curta duração.
- **Session:** histórico e estado da conversa atual; dura a sessão e pode gerar um resumo.
- **Episodic:** eventos relevantes associados a tempo e contexto; persistente quando útil.
- **Semantic:** fatos duradouros sobre usuário, projetos, preferências e ambiente; persistente.
- **Procedural:** maneiras como Gustavo prefere trabalhar e colaborar; persistente.
- **Knowledge:** documentos, código, notas e fontes indexadas; persistente e reindexável.

Esses tipos descrevem a direção arquitetural, não componentes já implementados. Cada tipo deve ser introduzido somente quando uma necessidade concreta surgir.

## Política de captura

- Hoje a captura ocorre somente quando o usuário solicita explicitamente por comando literal ou confirma uma proposta de criação natural no CLI.
- Não há captura automática de fatos, preferências ou eventos ainda.
- Evitar fatos passageiros sem utilidade futura.
- Perguntar quando a relevância for ambígua.
- Registrar origem, data, tipo e confiança quando possível.

## Estado atual

- Persistência JSON estruturada implementada por meio de `JsonMemoryDataSource`, em arquivo local quando o CLI é iniciado com um caminho explícito.
- `MemoryService` concentra identidade, datas, duplicidade, busca e edição e depende somente do contrato `MemoryRepository`.
- `LocalMemoryRepository` implementa `MemoryRepository`, delega persistência ao contrato `MemoryLocalDataSource` e traduz erros da fonte local para `MemoryRepositoryError`.
- `JsonMemoryDataSource` implementa a fonte local atual e concentra JSON, filesystem, cache lazy e escrita atômica. Um futuro `SqliteMemoryDataSource` poderá ocupar o mesmo limite sem alterar serviço ou repository.
- O CLI escolhe `JsonMemoryDataSource`, `LocalMemoryRepository` e `MemoryService` apenas no ponto de composição.
- Inclusão, edição e exclusão confirmada retornam resultados explícitos para casos esperados, como duplicidade, conflito e valores inválidos, sem sobrecarregar exceptions como controle de fluxo. Falhas de persistência usam o erro abstrato `MemoryRepositoryError`.
- As gravações usam arquivo temporário e substituição atômica; o cache só é atualizado depois que a persistência termina com sucesso.
- Cada memória possui `id` local estável, `content`, `source`, `created_at` e `updated_at`. A origem implementada neste incremento é `explicit_cli`, e as datas usam UTC em formato ISO 8601.
- O único formato aceito é uma lista JSON de objetos estruturados; listas de strings não são mais suportadas.
- JSON inválido não é tratado como lista vazia nem sobrescrito: o repositório reporta `MemoryRepositoryError`, e o CLI traduz a falha sem encerrar a sessão.
- A captura acontece por comando explícito (`lembrar:`) ou por pedido natural explícito que gere uma proposta e seja confirmado localmente no CLI.
- A listagem das memórias salvas está disponível no CLI via comando `memórias`.
- A remoção explícita de uma memória salva está disponível por meio do comando `esquecer:` com correspondência exata.
- A edição explícita de uma memória salva está disponível por meio do comando `editar memória: <texto atual> -> <novo texto>` com correspondência exata e sem duplicação.
- A pesquisa textual explícita de memórias salvas está disponível por meio do comando `buscar memória: <termo>` com correspondência parcial e sem distinção de maiúsculas/minúsculas.
- A edição natural do nome preserva os padrões determinísticos `Meu nome agora é <novo nome>` e `Mude meu nome para <novo nome>`; paráfrases passam pelo gate de nome, que tem precedência sobre os demais. O modelo apenas propõe o novo nome e não recebe IDs. O sistema localiza localmente uma única memória no formato `Meu nome é ...` ou `Eu me chamo ...`, apresenta o conteúdo atual e o novo conteúdo e só executa após confirmação explícita.
- A edição natural genérica usa um gate específico e `EditMemoryIntent` com query e novo conteúdo por JSON estrito. A seleção local tenta primeiro igualdade sem distinção de caixa e depois `MemoryService.search()`; zero ou múltiplas candidatas não geram escolha. Exatamente uma candidata reutiliza `PendingMemoryEdit`, e somente a confirmação chama `MemoryService.edit_by_id()` com ID e snapshot.
- A criação natural aceita somente pedidos explícitos de memorização. Os padrões completos `lembre que`, `memorize que`, `guarde que` e `não esqueça que` extraem deterministicamente uma única memória sem chamar o modelo; paráfrases passam pelo gate local e podem ser propostas pelo modelo mediante JSON estrito. Em ambos os caminhos o conteúdo integral é apresentado e `MemoryService.add()` só é chamado após confirmação explícita. Não existe captura automática de fatos durante conversas comuns.
- A exclusão natural aceita padrões completos como `esqueça que`, `remova a memória:` e `apague a memória:` ou paráfrases que passem por um gate específico e produzam JSON estrito. O modelo fornece somente uma query e não recebe IDs ou a lista de memórias. A seleção local tenta primeiro igualdade sem distinção de caixa e depois a pesquisa textual existente; exatamente uma candidata gera `PendingMemoryDelete`. Após confirmação, `MemoryService.delete_by_id()` valida ID e snapshot antes de persistir.
- A edição natural usa ID estável e snapshot do conteúdo esperado. ID inválido, memória ausente, conteúdo divergente ou duplicado não são persistidos. Comandos literais de memória continuam disponíveis e cancelam uma proposta pendente antes de executar.
- A prevenção de duplicatas compara uma chave privada com `strip`, Unicode NFKC, espaços consecutivos colapsados, `casefold` e remoção de um único ponto terminal. O conteúdo original continua sendo persistido sem essa normalização, e a equivalência não impede editar apenas a capitalização ou formatação da própria memória.
- Em cada interação conversacional, `ConversationService` consulta as memórias persistidas pelo contrato `MemoryReader` e delega ao `ContextBuilder` a inclusão do conteúdo na mensagem `system`, junto da identidade estável do Aska. O histórico da sessão segue em mensagens separadas com papéis `user` e `assistant`, inclusive quando as memórias vêm de execuções anteriores. O CLI apenas compõe e injeta o `MemoryService` e despacha os comandos de entrada.
- Das memórias, somente `content` é enviado ao modelo; IDs e metadados permanecem locais por padrão.

## Transparência e controle

O usuário deve poder listar, pesquisar, editar e excluir memórias, marcá-las como temporárias ou permanentes e desativar a captura automática. Listagem, pesquisa, edição e exclusão explícitas estão implementadas; temporalidade e configuração de captura automática continuam pendentes.

## Limitações atuais

- Todas as memórias salvas são enviadas em todas as requisições ao modelo; não há seleção por relevância.
- O conteúdo das memórias ainda é serializado como uma lista textual dentro da mensagem `system`; a estrutura e os metadados persistidos não são expostos ao modelo.
- Não há compactação, orçamento de tokens, tipos avançados ou explicabilidade além da origem e das datas mínimas.
- A interpretação por modelo está limitada às propostas de alteração do nome e criação, edição ou exclusão explícita de uma memória, sem tool calling. JSON inválido, campos ou ações desconhecidos e conteúdo vazio são rejeitados sem produzir proposta. Captura automática e ações de memória mais amplas permanecem `planned`.
- A interface atual é o CLI, mas detecção e representação da proposta não dependem dele e poderão ser reutilizadas por voz no futuro.
- O histórico da sessão continua separado e apenas em memória durante a execução atual.
- JSON continua sendo o armazenamento atual. SQLite é uma evolução provável quando consultas, volume ou atomicidade justificarem a mudança, mas ainda não foi adotado.
- O cache do `JsonMemoryDataSource` assume que a instância do CLI é a responsável pelas alterações durante sua execução; mudanças externas no arquivo não são recarregadas automaticamente.

## Dependências implementadas

```text
MemoryService
    ↓
MemoryRepository
    ↑ implementa
LocalMemoryRepository
    ↓
MemoryLocalDataSource
    ↑ implementa
JsonMemoryDataSource
```

`SqliteMemoryDataSource` continua `planned` e não foi criado neste incremento.

## Organização do package

```text
packages/memory/
├── domain/
│   ├── model.py
│   ├── repository.py
│   └── service.py
├── data/
│   ├── local_data_source.py
│   ├── local_repository.py
│   └── json_data_source.py
└── __init__.py
```

`domain` não depende de `data`. Cada camada possui seu próprio `__init__.py`, e o barrel raiz expõe a API pública completa para consumidores externos.
