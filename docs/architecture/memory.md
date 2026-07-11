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

- Memorizar quando o usuário pedir explicitamente.
- Capturar automaticamente apenas informações claramente duradouras e úteis.
- Evitar fatos passageiros sem utilidade futura.
- Perguntar quando a relevância for ambígua.
- Registrar origem, data, tipo e confiança quando possível.

## Transparência e controle

O usuário deve poder listar, pesquisar, editar e excluir memórias, marcá-las como temporárias ou permanentes e desativar a captura automática. O Aska deve conseguir explicar por que uma memória existe ou foi usada.

A escolha entre JSON, SQLite ou outra persistência simples continua aberta e deve ocorrer apenas no incremento que introduzir memória persistente.
