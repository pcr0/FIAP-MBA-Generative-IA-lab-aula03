# Trade-offs da Arquitetura

## 1. Build vs Buy: Por que criar MCP tools em vez de usar HTTP direto?

As novas tools foram projetadas para fundamentar a decisão fornecida pelos agentes de análise operacional e financeiro. Diferentemente de um endpoint REST padrão, as tools MCP permitem que o modelo interaja com o sistema ERP de maneira autônoma, o que amplia a sua capacidade de tomar decisões.

## 2. Maior Risco da Arquitetura Proposta

Grandes modelos de linguagem podem cometer erros e portanto gerar falsos positivos. Embora os pareceres retornados pelos agentes estejam disponíveis no momento da aprovação humana, o operador pode ser convencido pelo texto gerado pela inteligência artificial, o que pode levar a uma decisão equivocada.

## 3. Impacto do Budget: R$ 10 por Execução

Caso o orçamento fosse limitado a R$ 10 por execução, a arquitetura alternativa que utiliza o modelo Claude Opus como orquestrador em vez da pipeline n8n, se tornaria uma arquitetura viável financeiramente. Contudo, novas tools MCP deveriam ser criadas para que o modelo gerenciasse as aprovações.

## 4. Funcionalidades Não Implementadas

Durante a discussão, levantamos a possibilidade de implementar a anonimização de dados pessoais na API Rest do ERP. Uma implementação possível seria considerar a role do usuário que está fazendo a requisição à API. Neste modelo, o usuário de serviço utilizado pelo servidor MCP teria uma role específica que identificasse que um agente de IA está requisitando a API e, portanto, os dados pessoais devem ser anonimizados. Esta funcionalidade não foi incluída na solução por adicionar complexidade ao desenvolvimento.
