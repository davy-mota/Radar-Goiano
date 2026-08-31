# Plano técnico de evolução do Radar Goiano

## 1. Objetivo

Transformar o Radar Goiano em uma plataforma de exploração de gastos públicos com rastreabilidade, comparação temporal e alertas explicáveis. O sistema deve permitir que um indicador agregado seja investigado até o registro que lhe deu origem.

## 2. Estado atual

O projeto possui:

- frontend React/Vite com visão geral, contratos, folha e diárias;
- API FastAPI para leitura dos caches agregados;
- PostgreSQL com contratos, diárias, folha, pagamentos e receitas;
- geradores de cache JSON para os painéis agregados;
- aproximadamente 4,08 milhões de registros em `pagamentos_estaduais`, cobrindo 2003 a 2025.

Os caches continuarão sendo utilizados para telas agregadas. Consultas detalhadas serão feitas pela API com paginação, pois o volume não é apropriado para arquivos JSON públicos.

## 3. Arquitetura alvo

```text
Dados Abertos GO
      |
      v
Extratores e validação
      |
      v
PostgreSQL (fonte analítica)
      |                  |
      v                  v
Caches agregados      API paginada
      |                  |
      +--------+---------+
               v
          Frontend React
```

### Princípios

1. Fonte e data de atualização visíveis.
2. Paginação e agregação realizadas no servidor.
3. Parâmetros SQL sempre vinculados; ordenação limitada a uma lista segura.
4. Alertas descritos como indícios estatísticos, nunca como prova de irregularidade.
5. Cargas feitas em tabelas de preparação antes da substituição dos dados oficiais.
6. Compatibilidade com implantação local e configuração por ambiente.

## 4. Incremento 1: Explorador de Despesas

### Escopo

- KPIs de valores empenhados, liquidados, pagos e saldo liquidado a pagar;
- filtros por ano, mês, órgão, função e credor/empenho;
- série mensal de execução;
- ranking dos órgãos por valor pago;
- tabela detalhada paginada;
- ordenação por valor, data, credor ou órgão;
- estados de carregamento, erro e ausência de resultados.

### Endpoints

#### `GET /api/despesas/filtros`

Retorna anos, órgãos e funções disponíveis. O ano restringe as opções de órgão e função.

#### `GET /api/despesas/resumo`

Retorna KPIs, série mensal e os cinco órgãos com maior valor pago.

#### `GET /api/despesas`

Retorna registros detalhados e metadados de paginação.

Parâmetros comuns:

| Parâmetro | Tipo | Descrição |
|---|---:|---|
| `ano` | texto | Ano numérico ou `todos` |
| `mes` | inteiro | 1 a 12 |
| `orgao` | texto | Nome exato do órgão |
| `funcao` | texto | Função orçamentária |
| `busca` | texto | Credor, CPF/CNPJ ou empenho |
| `pagina` | inteiro | Página iniciada em 1 |
| `por_pagina` | inteiro | 10 a 100 registros |

### Desempenho

Os índices da migração `backend/migrations/001_indices_despesas.sql` atendem aos filtros mais frequentes. Em produção, a migração deve ser executada separadamente porque usa `CREATE INDEX CONCURRENTLY`.

### Critérios de aceitação

- nenhuma consulta detalhada retorna mais de 100 itens;
- filtros inválidos retornam HTTP 422;
- totais do resumo respeitam os mesmos filtros da listagem;
- erros de rede são apresentados ao usuário;
- lint, build e testes da API passam.

## 5. Incrementos seguintes

### Incremento 2 — Perfil do fornecedor (implementado)

- consolidação por CNPJ validado;
- contratos, empenhos e pagamentos relacionados;
- concentração por órgão e evolução anual;
- cruzamento futuro com cadastros oficiais de sanções.

#### Decisão de identidade

A associação automática foi restringida a CNPJs com dígitos verificadores válidos. A base de pagamentos possui identificadores ausentes, códigos internos e valores transformados em notação científica; esses registros não são ligados automaticamente. Nomes são exibidos como atributos e variações, nunca como chave de identidade.

Endpoints adicionados:

- `GET /api/fornecedores/{cnpj}/resumo`;
- `GET /api/fornecedores/{cnpj}/pagamentos`;
- `GET /api/fornecedores/{cnpj}/contratos`.

O perfil apresenta totais, período de relacionamento, evolução anual, órgãos pagadores, nomes encontrados, contratos e histórico paginado de pagamentos. A migração `002_indices_fornecedores.sql` cria índices funcionais para o CNPJ normalizado.

### Incremento 3 — Comparações (implementado)

- órgão contra órgão e período contra período;
- variação nominal e corrigida;
- indicadores per capita quando houver fonte populacional versionada.

A primeira versão implementa comparação nominal de dois cenários (`órgão + ano`), com execução mensal, funções, credores, concentração e variação percentual. Correção inflacionária e valores per capita permanecem como evoluções por dependerem de fontes externas versionadas.

Endpoint adicionado: `GET /api/comparacoes/orgaos`.

### Incremento 4 — Orçamento e receita (implementado)

- previsto, atualizado, empenhado, liquidado e pago;
- receita prevista versus arrecadada;
- percentuais e projeção de execução.

A primeira versão combina receita prevista, arrecadada e etapas da despesa por ano e mês. Como a cobertura do campo `valor_previsto` varia fortemente entre exercícios, o percentual de realização só é calculado quando ao menos 70% dos registros possuem previsão positiva. Projeções permanecem futuras por exigirem tratamento de sazonalidade e completude da carga.

Endpoints adicionados:

- `GET /api/fiscal/anos`;
- `GET /api/fiscal/resumo`.

### Incremento 5 — Alertas explicáveis (implementado)

- duplicidade potencial;
- concentração de fornecedor;
- crescimento abrupto;
- fracionamento temporal;
- valores atípicos comparados a grupos equivalentes.

Cada alerta deverá registrar regra, parâmetros, população comparada e limitações.

A primeira versão implementa quatro regras determinísticas: duplicidade potencial, concentração em favorecido, crescimento mensal abrupto e pagamento atípico por IQR dentro da função governamental. A API limita a exibição a 25 evidências por regra, mas informa a quantidade total de ocorrências.

Endpoint adicionado: `GET /api/alertas`.

### Incremento 6 — Rastreabilidade e exportação (implementado)

- exportação CSV dos filtros do Explorador de Despesas;
- limite de 10 mil registros por arquivo;
- neutralização de fórmulas em planilhas;
- mascaramento de CPF e preservação de CNPJ;
- filtros e aba persistidos na URL;
- painel de proveniência, cobertura e completude;
- links para as fontes oficiais.

Endpoints adicionados:

- `GET /api/despesas/exportar.csv`;
- `GET /api/metadados`.

A maior data encontrada em um conjunto é apresentada como data de referência, não como data de extração. O histórico formal de cargas será coletado prospectivamente em uma evolução futura.

Os indicadores de qualidade são materializados pela migração `006_metadados_qualidade.sql` para que o painel não execute agregações completas a cada acesso. Após uma nova carga, a atualização é feita com `python atualizar_metadados.py` a partir da pasta `backend`.

### Incremento 7 — Histórico de cargas (implementado)

- registro prospectivo de início e término das importações;
- estados `em_execucao`, `sucesso` e `falha`;
- duração, quantidade final de registros, fonte e mensagem de erro;
- executor central com lista fechada de conjuntos permitidos;
- atualização automática dos metadados após uma carga bem-sucedida;
- histórico visível no painel de Qualidade dos Dados.

Endpoint adicionado: `GET /api/cargas`, com filtro opcional por conjunto e limite entre 1 e 100 registros.

As cargas devem ser iniciadas pela pasta `backend` com `python executar_carga.py <conjunto>`. Os conjuntos aceitos são `pagamentos`, `receitas`, `contratos`, `folha` e `diarias`. A migração `007_historico_cargas.sql` cria a estrutura de auditoria. Execuções anteriores não são reconstruídas, pois não existem evidências confiáveis de seus horários e resultados.

### Incremento 8 — Auditoria e reconstrução da camada de dados (implementado)

A auditoria de 28 de agosto de 2026 encontrou duplicação confirmada em receitas, duplicidades potenciais e diferença de versão em pagamentos, além de incompatibilidade entre o esquema atual da fonte e o extrator legado. O relatório reproduzível está em `docs/AUDITORIA_QUALIDADE_DADOS.md` e as consultas somente leitura em `backend/auditoria_qualidade.sql`.

A versão 11 foi validada e ativada após carga isolada por staging. O executor legado continua bloqueando pagamentos e receitas para impedir regressão ao fluxo que produzia sobreposição. A interface informa que a base é auditada e versionada e mantém o cuidado de apresentar alertas somente como indícios analíticos.

A migração `008_camadas_financeiras_versionadas.sql` criou as tabelas versionadas `fatos_empenhos`, `fatos_liquidacoes`, `fatos_pagamentos` e `fatos_receitas`, além de `versoes_dados` (um lote de carga, com status `preparando`/`validada`/`ativa`/`rejeitada`/`arquivada`) e `recursos_ingestao` (proveniência: URL, identificador CKAN, data de modificação e hash SHA-256 por arquivo). A migração `009_ano_exercicio_fatos.sql` acrescenta `ano_exercicio`, separando o ano do movimento do exercício orçamentário da fonte.

`backend/carga_financeira_versionada.py` carrega uma versão isolada, sem tocar nas tabelas legadas, selecionando apenas recursos anuais independentes e mensais do ano corrente. A validação bloqueante (`validar_versao`) rejeita a versão se houver meses/anos inválidos, soma nula, sobreposição de conteúdo entre recursos (via hash `chave_conteudo`) ou exercício divergente do parâmetro informado. A primeira execução completa (28 de agosto de 2026) produziu a versão 10: 1.289.486 empenhos, 2.948.640 liquidações, 2.819.715 pagamentos e 160.329 receitas.

`backend/ativar_versao.py` promove uma versão `validada` para `ativa`, ou reverte para uma versão `arquivada`, em uma única transação; o índice único parcial `idx_uma_versao_ativa` garante no banco que nunca haja duas versões ativas simultaneamente. Antes de ativar, reconsulta o catálogo oficial por recurso e bloqueia a ativação se algum tiver sido removido da fonte (contornável com `--ignorar-divergencias`). Cada ativação/reversão é registrada em `historico_cargas` (conjunto `ativacao_versao`), reaproveitando o endpoint `GET /api/cargas` do Incremento 7. A versão 10 foi ativada nesta execução: `vw_pagamentos_ativos` e `vw_empenhos_ativos` passaram a retornar 2.819.715 e 1.289.486 registros, respectivamente.

Os cinco controllers que liam as tabelas legadas (`rotas_despesas.py`, `rotas_alertas.py`, `rotas_comparacoes.py`, `rotas_fiscal.py`, `rotas_fornecedores.py`) foram migrados para `vw_pagamentos_ativos`/`vw_empenhos_ativos`/`vw_liquidacoes_ativas`/`vw_receitas_ativas`. A migração expôs dois defeitos pré-existentes na base legada: `valor_empenhado`/`valor_liquidado` estavam sempre zerados em `pagamentos_estaduais` (o extrator legado os define incondicionalmente como `0`), e o campo `funcao` estava 0% preenchido em produção (o arquivo oficial atual não publica esse campo), portanto o filtro de função do Explorador de Despesas e o agrupamento "por função" da Regra 4 de alertas nunca funcionaram de fato. A migração corrige os dois: KPIs de empenhado/liquidado agora refletem valores reais (somas independentes por fato, já que não há junção linha a linha confiável entre empenhos/liquidações/pagamentos), o filtro de função foi removido das telas, e a Regra 4 passou a agrupar por órgão ("Pagamentos atípicos por órgão"). Detalhes, números e a migração de índices (`010_indices_fatos_consulta.sql`) estão registrados em `docs/MEMORIAL_IMPLEMENTACAO_TCC.md`, incremento 8.

A verificação incluiu chamadas HTTP reais contra o PostgreSQL e uma checagem visual com Playwright headless, que revelou um terceiro defeito: 109 de 335 nomes de órgão em `fatos_pagamentos` estavam com mojibake (bytes UTF-8 decodificados como Latin-1) por uma falha na detecção de codificação de `carga_financeira_versionada.py` — corrigida (`detectar_codificacao`). Uma nova carga (versão 11) foi executada e ativada no mesmo dia, com os mesmos totais de registros da versão 10 e sem mojibake (confirmado a partir dos bytes brutos da resposta HTTP e visualmente no navegador).

A migração `011_metadados_qualidade_versionada.sql` atualizou `atualizar_metadados_qualidade()` para calcular os conjuntos `pagamentos` e `receitas` a partir de `vw_pagamentos_ativos`/`vw_receitas_ativas`, em vez das tabelas legadas; `contratos`, `folha` e `diarias` continuam inalterados, pois não fazem parte da reconstrução. `ativar_versao.py` passou a chamar `atualizar_metadados_qualidade()` dentro da mesma transação de troca de versão, para que o painel de Qualidade dos Dados nunca fique defasado em relação à versão ativa. `--reverter` foi exercitado de fato: a versão 11 foi revertida para a 10 (confirmando que `vw_pagamentos_ativos` voltou a servir os nomes de órgão com mojibake da versão 10) e depois revertida de volta para a 11, restaurando o estado limpo.

`backend/tests/test_integracao_endpoints.py` (novo) usa `TestClient` contra o FastAPI real e o PostgreSQL real — não `sqlite://` — para testar os endpoints migrados, incluindo dois testes de regressão específicos: `kpis.empenhado`/`kpis.liquidado` devem ser maiores que zero, e a resposta de `/api/despesas/filtros` não deve mais conter a chave `funcoes`. Os testes se autodesativam (`skipUnless`) se não houver PostgreSQL real com uma versão `ativa` disponível. A suíte cresceu para 30 testes (22 unitários + 8 de integração), executando em aproximadamente 70 segundos — bem mais lenta que os testes unitários puros (o dobro de ordens de grandeza), por consultar tabelas de milhões de linhas; aceitável para uma suíte que roda sob demanda, não a cada commit.

### Incremento 9 — Operação reproduzível e testes end-to-end (implementado)

- Playwright configurado para executar no Microsoft Edge local, sem instalar outro navegador;
- teste E2E das nove áreas da interface, falhas de rede, erros JavaScript e persistência da URL;
- testes unitários das regras de bloqueio, ativação forçada e reversão de versões;
- `scripts/radar.ps1` para iniciar, consultar e validar PostgreSQL, API e frontend;
- `scripts/atualizar_caches.ps1` para geração explícita por ano ou consolidado, seguida de validação JSON e comparação das cópias publicadas;
- correção da ressalva visual antiga, que ainda dizia que a recarga validada estava pendente.

### Incremento 10 — Storytelling e alfabetização de dados (implementado)

A antiga Visão Geral foi substituída pelo “Resumo Cidadão”, organizado como uma leitura guiada: escopo, concentração, pontos de atenção e investigação. A tela deixa de exibir a soma de folha, contratos e diárias como “custo total”, pois esses conjuntos têm naturezas distintas e sua adição produziria um indicador semanticamente inadequado. O gráfico de “distribuição do orçamento” foi removido pela mesma razão.

O resumo apresenta definições em linguagem simples, ressalvas próximas dos números, glossário de execução orçamentária e chamadas para aprofundamento nas telas de Folha, Alertas e Explorador de Despesas. Expressões potencialmente acusatórias, como “empresa favorita”, foram retiradas. Os maiores valores são descritos como pontos que merecem contexto, nunca como irregularidades. O teste E2E passou a verificar explicitamente a presença da ressalva semântica e a ausência do antigo “CUSTO TOTAL AUDITADO”.

O mesmo método foi aplicado às demais telas por meio do componente compartilhado `ContextoTela`: cada área declara a pergunta que responde e como seus resultados devem ser interpretados. Foram contemplados Explorador, Comparador, Fiscal, Alertas, Qualidade, Contratos, Folha, Diárias e Perfil do Fornecedor. O roadmap de novas fontes está documentado em `docs/ROADMAP_DADOS_RELEVANTES.md`.

### Incremento 11 — Políticas públicas e natureza da despesa (implementado)

O conjunto oficial “Execução Orçamentária Natureza Despesa” foi incorporado em lote versionado próprio. Ele já contém função, subfunção, programa, ação, categoria, grupo, modalidade, elemento, órgão e valores empenhado, liquidado e pago; por isso o conjunto “Funcional” não foi carregado em paralelo, evitando duplicação. A carga inicial reuniu os sete recursos mensais independentes de 2026: 28.567 registros e cobertura de janeiro a julho. A nova tela “Políticas Públicas” traduz os lançamentos em funções governamentais e explicita que classificação orçamentária não mede, isoladamente, resultado ou qualidade do serviço.

### Incremento 12 — Repasses aos municípios (implementado)

Foram carregados em lote versionado os sete recursos mensais independentes publicados para 2025. A base ativa contém 11.115 registros, janeiro a julho, e R$ 3,62 bilhões creditados em ICMS, IPI e IPVA. A primeira versão da tela territorial separou créditos e deduções do Fundeb, apresentou a cobertura parcial e adiou a comparação per capita até a implantação da dimensão populacional descrita no Incremento 13.

### Incremento 13 — Dimensão municipal e população versionada (implementado)

O cadastro oficial de localidades do IBGE foi incorporado com os 246 códigos municipais de Goiás, regiões imediatas e intermediárias. A estimativa populacional de 2025 foi armazenada por código IBGE e ano, com referência em 1º de julho e URL de proveniência. A carga é idempotente e exige exatamente 246 municípios antes de persistir os dados.

A auditoria esclareceu as 247 grafias da fonte de repasses: `BOM JESUS` foi conciliado de forma manual e rastreável com Bom Jesus de Goiás (código 5203500), enquanto `MUNICIPIO NAO INFORMADO` foi mantido sem vínculo. Assim, os dados cobrem os 246 municípios oficiais; 45 lançamentos sem identificação territorial ficam fora dos rankings, mas permanecem nos totais estaduais.

A API e a tela passaram a oferecer duas leituras alternáveis: valor total e valor por habitante. O denominador usa a população do mesmo exercício dos repasses. A interface esclarece que o indicador per capita é uma razão analítica e não um pagamento entregue diretamente a cada morador.

### Incremento 14 — Mapa municipal interativo (implementado)

A malha municipal oficial mais recente do IBGE foi armazenada localmente em GeoJSON de qualidade mínima, com 246 feições identificadas por `codarea`. O arquivo local elimina uma dependência de rede durante a navegação e mantém correspondência integral com os 246 códigos devolvidos pela API de repasses.

O mapa coroplético foi implementado em SVG sem biblioteca cartográfica adicional. O componente calcula a projeção para o espaço disponível, suporta geometrias `Polygon` e `MultiPolygon` e distribui os valores em cinco faixas quantílicas. A mesma seleção da tela alterna o mapa entre valor total e valor por habitante, evitando divergência entre mapa e ranking.

Cada município pode ser acessado por mouse ou teclado. A seleção apresenta nome, código IBGE, população, total creditado e razão per capita. A legenda explica que tons escuros representam posição relativa entre os municípios e não avaliação de qualidade da gestão pública.

### Incremento 15 — Perfil detalhado de repasses municipais (implementado)

A seleção de um território passou a abrir um perfil analítico solicitado pelo código IBGE e pelo exercício. O endpoint calcula composição de ICMS, IPVA e IPI, dedução do Fundeb, evolução mensal, posição entre os 246 municípios nos valores absoluto e per capita e informações das regiões geográficas imediata e intermediária.

O storytelling divide a investigação em três perguntas: de quais tributos veio o valor, como os créditos evoluíram e como o município se compara a localidades de porte próximo. A comparação usa os cinco municípios com população numericamente mais próxima e apresenta a diferença percentual de população. Essa opção mantém a análise disponível para casos sem pares próximos, como Goiânia, e a interface alerta que população semelhante não implica estrutura econômica ou arrecadatória equivalente.

### Incremento 16 — Emendas parlamentares estaduais (implementado)

O conjunto oficial da SERINT foi incorporado em lote versionado. Embora o recurso seja denominado “2025”, o arquivo contém 10.976 registros dos exercícios de 2020 a 2025; a carga filtra explicitamente o exercício solicitado e registra o descarte nas métricas. Para 2025 foram ativados 417 registros, R$ 83,03 milhões indicados, R$ 84,06 milhões empenhados, R$ 68,71 milhões liquidados e R$ 51,99 milhões pagos.

Doze valores monetários `#N/D` foram tratados como ausentes nas somas e contabilizados na qualidade do lote. O campo “Número PDF” foi publicado em notação científica, com perda de unicidade, e por isso não foi usado como chave. A deduplicação utiliza hash integral do conteúdo. Dos registros de 2025, 147 municípios foram conciliados pelo código IBGE e 17 linhas permaneceram sem vínculo territorial.

A nova tela organiza a leitura como trajetória financeiro-orçamentária, sem somar etapas: indicado, empenhado, liquidado e pago. Também apresenta autores, funções, beneficiários e maiores registros, com ressalvas contra interpretações de favorecimento ou irregularidade baseadas apenas em volume.

#### Obras públicas — limitação da fonte identificada

A prioridade de Obras foi investigada antes de Emendas. O Estado publica informações detalhadas do GOMAP em dois relatórios públicos do Power BI, mas não foi localizado CSV, recurso CKAN ou endpoint oficial documentado para ingestão. A extração do protocolo interno do Power BI foi rejeitada por fragilidade operacional e baixa reprodutibilidade acadêmica. Obras permanece no roadmap aguardando exportação estruturada oficial.

### Incremento 17 — Perfil do Governador (implementado)

- remuneração mensal do cargo de Governador na folha de pagamento estadual, do primeiro mês disponível (janeiro de 2012) até o último (dezembro de 2025);
- identificação dos mandatos (nome, início e fim) derivada da própria série mensal, sem cadastro externo de mandatos;
- comparação da remuneração bruta com o teto constitucional vigente;
- diárias vinculadas à estrutura da Governadoria (gabinete, ajudância de ordens, segurança), por ano.

#### `GET /api/governador/resumo`

Sem parâmetros. Retorna KPIs acumulados, a série mensal completa, os mandatos identificados e o resumo de diárias da Governadoria.

#### Desempenho

A consulta filtra `folha_pagamento` (52 milhões de linhas) por `LOWER(cargo)`, sem índice de apoio; a primeira medição levou aproximadamente 39 segundos. A migração `017_indice_cargo_folha.sql` cria `idx_folha_cargo_lower` (`CREATE INDEX CONCURRENTLY` sobre `LOWER(cargo)`), reduzindo o tempo de resposta para aproximadamente 0,8 segundo.

#### Decisão de identidade

Diferente do Perfil do Fornecedor, aqui a chave de identidade é o cargo (`Governador do Estado` e sua grafia atual `Governador - DSE-1`), não um documento validado, porque não há CPF/CNPJ estável e público para vincular a pessoa ao longo dos mandatos. O nome retornado descreve quem ocupava o cargo em cada mês, não uma chave de busca.

#### Critérios de aceitação

- a resposta cobre a série mensal completa, sem paginação (menos de 200 pontos);
- a consulta responde em menos de 2 segundos com o índice aplicado;
- diárias da Governadoria nunca são apresentadas como viagens pessoais do titular do cargo, pois a fonte oficial não publica lançamentos de diária em nome do Governador.

### Incremento 18 — Cota parlamentar de deputados federais e senadores (implementado)

- gasto por parlamentar (ranking), categoria de despesa e evolução mensal, para deputados federais e senadores eleitos por Goiás;
- seletor de exercício e alternância entre os dois cargos na mesma tela;
- carga versionada por exercício, com lote isolado e validação bloqueante antes da ativação.

#### `GET /api/parlamentares/anos`

Sem parâmetros. Retorna os exercícios com lote ativo, separadamente para deputados e para senadores.

#### `GET /api/parlamentares/deputados/resumo?ano=AAAA`

KPIs (total líquido, deputados com lançamento, lançamentos), ranking por deputado, maiores categorias de despesa e série mensal.

#### `GET /api/parlamentares/senadores/resumo?ano=AAAA`

Mesmo formato, para senadores.

#### Fontes e identidade

Deputados federais: Cota para Exercício da Atividade Parlamentar (CEAP), arquivo consolidado anual `https://www.camara.leg.br/cotas/Ano-AAAA.csv.zip`, filtrado pela coluna `sgUF = 'GO'`. A identidade do parlamentar usa `ideCadastro` (id numérico estável, o mesmo da API `dadosabertos.camara.leg.br/api/v2/deputados`), não o nome — deliberadamente diferente de `nuDeputadoId`, um segundo identificador presente no mesmo arquivo que não corresponde ao id da API atual.

Senadores: Cota para Exercício da Atividade Parlamentar dos Senadores (CEAPS), obtida pelo endpoint administrativo oficial `https://adm.senado.gov.br/adm-dadosabertos/api/v1/senadores/despesas_ceaps/AAAA/csv`. A seleção de Goiás é conciliada com a lista oficial da legislatura e a identidade persistida usa `COD_SENADOR`, presente no CSV.

#### Modelagem e desempenho

Segue o modelo de lote/fato de Emendas e Repasses (`lotes_deputados`/`fatos_despesas_deputados`, `lotes_senadores`/`fatos_despesas_senadores`, migração `018_despesas_parlamentares.sql`), com uma adaptação deliberada: o índice de lote ativo é único por `(status, ano)`, não por tabela inteira. Emendas e Repasses usam um índice único por tabela inteira porque, até esta entrega, carregaram apenas um exercício cada; aqui a tela exibe série histórica (2019–2026), e um índice único por tabela ativaria no máximo um exercício por vez, esvaziando os demais anos da view a cada nova carga.

#### Critérios de aceitação

- cada exercício mantém seu próprio lote ativo, independente dos demais;
- a resposta distingue parlamentar cadastrado sem documento de parlamentar com valor efetivamente reembolsado;
- ausência de um parlamentar em um exercício não é tratada como erro — a carga só falha se não houver nenhum registro de Goiás no arquivo daquele ano.

### Evolução do Incremento 18 — triagem comparativa e cobertura institucional

A tela passou a consumir `GET /api/parlamentares/resumo?ano=AAAA`, que entrega uma comparação homogênea por cargo. Para cada parlamentar com documentos, o contrato informa total reembolsado, glosas, quantidade de documentos, meses com registros, média mensal, maior documento, maior mês, categoria principal e sua concentração. A API calcula também mediana, média, posição e percentil dentro da coorte do mesmo cargo.

O indicador visual “acima da mediana” é somente uma regra de priorização documental: média mensal pelo menos 25% superior à mediana e coorte com dez ou mais integrantes. Ele não afirma excesso, desperdício ou irregularidade. Para senadores, a coorte goiana é pequena e a interface exibe “amostra pequena” em vez de classificar o gasto.

A cobertura distingue parlamentares cadastrados, com documentos e sem documentos. Ausência na CEAPS é mostrada como “sem registro na fonte”, nunca como despesa igual a zero. Deputados estaduais usam o resumo mensal oficial da verba indenizatória da Alego. Vereadores permanecem pendentes porque as 246 câmaras municipais não possuem uma fonte estruturada centralizada; nenhuma lacuna é convertida em zero.

Na carga consolidada de 2025, deputados usam `ideCadastro`; senadores usam `COD_SENADOR`, conciliado com a lista oficial da 57ª Legislatura. A CEAPS é obtida pela API administrativa oficial do Senado (`/adm-dadosabertos/api/v1/senadores/despesas_ceaps/AAAA/csv`).

#### Integração da Alego

A fonte estadual é `GET /api/transparencia/verbas_indenizatorias.json?ano=AAAA&mes=M&todos=true`. A carga consulta os períodos publicados e faz uma requisição consolidada por mês, evitando centenas de chamadas individuais ao portal. Cada registro preserva o identificador da prestação, o identificador e nome do deputado, valor apresentado, valor indenizado e a diferença entre ambos. O link do detalhe oficial permanece associado ao registro.

A granularidade estadual é mensal por gabinete. Consequentemente, a contagem mostrada é de prestações mensais, não de notas fiscais, e categorias/fornecedores não são inferidos do resumo. Em 2025 foram integradas 492 prestações de 44 parlamentares que apareceram em pelo menos um mês; o número pode superar as 41 cadeiras porque inclui substituições ocorridas ao longo do exercício.

## 6. Qualidade, segurança e observabilidade

- testes unitários para normalização monetária e filtros;
- testes de integração dos endpoints;
- limites de paginação e tamanho da busca;
- medição de duração e contagem de resultados das consultas;
- relatório de cobertura, rejeições e data da última carga;
- credenciais somente em variáveis de ambiente;
- origens CORS explícitas para `localhost` e `127.0.0.1` no desenvolvimento;
- política de retenção e minimização para identificadores pessoais.

## 7. Definição de pronto

Uma feature está pronta quando possui contrato de API documentado, validação, estado de erro no frontend, teste automatizado, consulta indexada quando necessário e origem dos dados identificada.
