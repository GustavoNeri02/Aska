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

- Persistência JSON estruturada já implementada por meio de `JsonMemoryStore`, em arquivo local quando o CLI é iniciado com um caminho explícito.
- A entidade `Memory` e o contrato `MemoryRepository` ficam separados do adaptador `JsonMemoryStore`; o CLI depende do contrato e escolhe JSON apenas no ponto de composição.
- Cada instância de `JsonMemoryStore` carrega o arquivo de forma lazy e mantém as memórias em cache durante o processo, evitando leitura e desserialização repetidas em listagens, buscas e construção de contexto.
- Cada memória possui `id` local estável, `content`, `source`, `created_at` e `updated_at`. A origem implementada neste incremento é `explicit_cli`, e as datas usam UTC em formato ISO 8601.
- O único formato aceito é uma lista JSON de objetos estruturados; listas de strings não são mais suportadas.
- JSON inválido não é sobrescrito por operações de escrita; o armazenamento recusa a mutação para evitar perda silenciosa.
- A captura acontece somente por comando explícito (`lembrar:`) no CLI.
- A listagem das memórias salvas está disponível no CLI via comando `memórias`.
- A remoção explícita de uma memória salva está disponível por meio do comando `esquecer:` com correspondência exata.
- A edição explícita de uma memória salva está disponível por meio do comando `editar memória: <texto atual> -> <novo texto>` com correspondência exata e sem duplicação.
- A pesquisa textual explícita de memórias salvas está disponível por meio do comando `buscar memória: <termo>` com correspondência parcial e sem distinção de maiúsculas/minúsculas.
- Em cada interação conversacional, o CLI carrega as memórias persistidas e as inclui no prompt enviado ao modelo, junto com o histórico da sessão, inclusive em novas execuções.
- O contexto enviado ao modelo contém somente `content`; identidade e metadados permanecem locais por padrão.

## Transparência e controle

O usuário deve poder listar, pesquisar, editar e excluir memórias, marcá-las como temporárias ou permanentes e desativar a captura automática. No estado atual, essa capacidade ainda é parcial e limitada à listagem explícita via CLI.

## Limitações atuais

- Todas as memórias salvas são enviadas em todas as requisições ao modelo; não há seleção por relevância.
- O contexto é serializado como texto livre pelo CLI; a estrutura e os metadados persistidos não são expostos ao modelo.
- Não há compactação, orçamento de tokens, tipos avançados ou explicabilidade além da origem e das datas mínimas.
- O histórico da sessão continua separado e apenas em memória durante a execução atual.
- JSON continua sendo o armazenamento atual. SQLite é uma evolução provável quando consultas, volume ou atomicidade justificarem a mudança, mas ainda não foi adotado.
- O cache assume que a instância do CLI é a responsável pelas alterações durante sua execução; mudanças externas no arquivo não são recarregadas automaticamente.
