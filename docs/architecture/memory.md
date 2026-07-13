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

- Hoje a captura ocorre somente quando o usuário solicita explicitamente via comando de memória no CLI.
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
- Inclusão e edição retornam resultados explícitos para casos esperados, como duplicidade e valores inválidos, sem sobrecarregar exceptions como controle de fluxo. Falhas de persistência usam o erro abstrato `MemoryRepositoryError`.
- As gravações usam arquivo temporário e substituição atômica; o cache só é atualizado depois que a persistência termina com sucesso.
- Cada memória possui `id` local estável, `content`, `source`, `created_at` e `updated_at`. A origem implementada neste incremento é `explicit_cli`, e as datas usam UTC em formato ISO 8601.
- O único formato aceito é uma lista JSON de objetos estruturados; listas de strings não são mais suportadas.
- JSON inválido não é tratado como lista vazia nem sobrescrito: o repositório reporta `MemoryRepositoryError`, e o CLI traduz a falha sem encerrar a sessão.
- A captura acontece somente por comando explícito (`lembrar:`) no CLI.
- A listagem das memórias salvas está disponível no CLI via comando `memórias`.
- A remoção explícita de uma memória salva está disponível por meio do comando `esquecer:` com correspondência exata.
- A edição explícita de uma memória salva está disponível por meio do comando `editar memória: <texto atual> -> <novo texto>` com correspondência exata e sem duplicação.
- A pesquisa textual explícita de memórias salvas está disponível por meio do comando `buscar memória: <termo>` com correspondência parcial e sem distinção de maiúsculas/minúsculas.
- Em cada interação conversacional, o CLI carrega as memórias persistidas e as inclui no prompt enviado ao modelo, junto com o histórico da sessão, inclusive em novas execuções.
- O contexto enviado ao modelo contém somente `content`; identidade e metadados permanecem locais por padrão.

## Transparência e controle

O usuário deve poder listar, pesquisar, editar e excluir memórias, marcá-las como temporárias ou permanentes e desativar a captura automática. Listagem, pesquisa, edição e exclusão explícitas estão implementadas; temporalidade e configuração de captura automática continuam pendentes.

## Limitações atuais

- Todas as memórias salvas são enviadas em todas as requisições ao modelo; não há seleção por relevância.
- O contexto é serializado como texto livre por `ContextBuilder`; a estrutura e os metadados persistidos não são expostos ao modelo.
- Não há compactação, orçamento de tokens, tipos avançados ou explicabilidade além da origem e das datas mínimas.
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
