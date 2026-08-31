# Roadmap de dados relevantes para o Radar Goiano

## Critério de priorização

Um novo conjunto deve ajudar o cidadão a responder pelo menos uma destas perguntas:

1. quanto foi planejado, contratado, executado e pago;
2. onde o recurso chegou territorialmente;
3. quem recebeu e por qual instrumento;
4. qual política pública foi financiada;
5. quais resultados sociais podem ser acompanhados, sem inferir causalidade automática.

Também são considerados formato aberto, estabilidade da fonte, identificador oficial,
cobertura histórica e possibilidade de versionamento.

## Prioridade 1 — completar o caminho do dinheiro

### Execução por função, natureza e elemento da despesa

Permite traduzir códigos contábeis em perguntas cidadãs como “quanto foi destinado a
saúde, educação ou segurança?” e “o recurso financiou pessoal, investimento ou custeio?”.
É o complemento mais importante do Explorador de Despesas.

Fonte: Portal de Dados Abertos de Goiás, conjuntos **Execução Orçamentária Funcional**
e **Execução Orçamentária Natureza da Despesa**:
https://dadosabertos.go.gov.br/pt_BR/dataset/?res_format=CSV&tags=or%C3%A7amento

### Obras públicas

Adicionar município, área, situação, prazo, contratado, valor previsto, valor executado
e atraso permitiria contar a trajetória “recurso autorizado → obra contratada → entrega”.
A integração deve preservar a data de atualização e não classificar atraso sem considerar
paralisações formalizadas e alterações contratuais.

Fonte: Portal da Transparência de Goiás, seção Obras do Estado:
https://transparencia.go.gov.br/perguntas-frequentes/

### Repasses aos municípios

Mostra como ICMS, IPVA e outras receitas estaduais chegam a cada município. É adequado
para mapa, série temporal, valor por habitante e participação na receita local.

Fonte: Portal de Dados Abertos de Goiás, conjunto **Repasses**, série desde 2014:
https://dadosabertos.go.gov.br/pt_BR/dataset/?res_format=CSV&tags=or%C3%A7amento

### Emendas parlamentares

Permite acompanhar autor, município ou entidade beneficiada, finalidade, valor previsto,
empenhado, pago e situação. A narrativa deve separar emendas estaduais, federais e
transferências especiais.

Fonte: Portal da Transparência de Goiás:
https://transparencia.go.gov.br/emendas-parlamentares/

## Prioridade 2 — explicar instrumentos e beneficiários

### Licitações, contratos, aditivos e pagamentos conectados

O site já possui contratos, mas precisa incorporar licitação, vigência, aditivos e situação
para evitar interpretar valor inicial como execução financeira. A ligação só deve ocorrer
por número de processo, contrato ou outro identificador oficial, nunca apenas por nome.

Fonte de contratos, série 1998–atual e atualização mensal:
https://dadosabertos.go.gov.br/dataset/contratos

### Convênios e transferências voluntárias

Permite mostrar concedente, convenente, objeto, vigência, valor, contrapartida, liberação
e prestação de contas. É particularmente relevante para obras e serviços executados em
parceria com municípios ou organizações sociais.

Fonte: Portal de Dados Abertos de Goiás:
https://dadosabertos.go.gov.br/dataset/convenios

### Sanções de fornecedores

O cruzamento por CNPJ com CEIS, CNEP e cadastros estaduais acrescenta contexto ao perfil
do fornecedor. A tela deve apresentar tipo, órgão sancionador, início, fim e fonte, sem
tratar homônimos ou sanções expiradas como impedimento atual.

Fonte federal oficial: Portal da Transparência/Controladoria-Geral da União:
https://portaldatransparencia.gov.br/sancoes

## Prioridade 3 — relacionar recursos e resultados

### População e indicadores municipais

População versionada viabiliza valores per capita. O Índice de Desempenho dos Municípios
do Instituto Mauro Borges reúne dimensões de saúde, educação, infraestrutura, economia,
trabalho e segurança e pode contextualizar o território.

Fonte: Instituto Mauro Borges:
https://goias.gov.br/imb/estudos/

### Indicadores setoriais de saúde, educação e segurança

Exemplos: filas e produção assistencial, matrículas e desempenho escolar, ocorrências e
taxas por população. Esses dados permitem comparar evolução de gasto e evolução de
resultado, mas o sistema deve declarar que correlação temporal não comprova causalidade.

Catálogo oficial do Estado:
https://dadosabertos.go.gov.br/

## Prioridade 4 — autoridades públicas (deputados, senadores, vereadores, Governador)

Investigado em 31 de agosto de 2026, a pedido de uma tela que reúna as principais métricas de
gasto de deputados, vereadores, senadores e do Governador.

- **Governador**: já presente na base local (`folha_pagamento`, `diarias_passagens`), sem
  necessidade de nova fonte. Implementado no Incremento 17 (`docs/MEMORIAL_IMPLEMENTACAO_TCC.md`).
- **Deputados federais por Goiás** e **Senadores por Goiás**: implementados no Incremento 18
  (`docs/MEMORIAL_IMPLEMENTACAO_TCC.md`). O endpoint por deputado da API da Câmara
  (`/api/v2/deputados/{id}/despesas`) mostrou-se persistentemente limitado (retorno vazio com
  `retry-after: 30`, mesmo após aguardar); a carga usa o arquivo consolidado anual
  `camara.leg.br/cotas/Ano-AAAA.csv.zip`, filtrado por UF. Senadores usam o CSV anual
  `senado.leg.br/transparencia/LAI/verba/despesa_ceaps_AAAA.csv`, sem UF nem id estável na
  fonte — associados a Goiás por nome normalizado contra a lista de titulares/suplentes das
  três vagas do estado.
- **Deputados estaduais (Alego)**: o Portal da Transparência da Alego
  (`transparencia.al.go.leg.br`) anuncia extrato de verba indenizatória “no mesmo modelo da
  Câmara dos Deputados”, mas é uma SPA que não permitiu confirmação automatizada de um
  endpoint ou CSV estável. Requer inspeção manual do portal antes de comprometer prazo de
  ingestão.
- **Vereadores**: sem fonte estruturada confiável em escala — Goiás tem 246 câmaras
  municipais independentes. A Câmara Municipal de Goiânia (a maior) publica apenas 4
  datasets JSON institucionais/legislativos em `goiania.go.leg.br/transparencia/dados-abertos`,
  sem indicação clara de verba indenizatória por lançamento. Mesmo padrão de bloqueio já
  registrado para Obras públicas: aguarda exportação estruturada oficial antes de entrar no
  cronograma.

## Ordem de implementação recomendada

1. execução por função/natureza da despesa;
2. repasses aos municípios e população versionada;
3. obras públicas;
4. emendas parlamentares;
5. licitações, aditivos e vínculo contrato–pagamento;
6. convênios;
7. sanções por CNPJ;
8. indicadores de resultado de saúde, educação e segurança.

Cada ingestão deve reutilizar o modelo versionado do projeto: staging, hash do recurso,
validação bloqueante, ativação transacional, proveniência e possibilidade de reversão.
