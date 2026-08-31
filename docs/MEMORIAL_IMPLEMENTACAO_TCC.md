# Memorial técnico de implementação para o TCC

## Incremento 16 — Emendas parlamentares e qualidade da fonte

A fonte oficial da Secretaria de Estado de Relações Institucionais disponibiliza autor,
objeto, beneficiário, município, função orçamentária e valores de indicação, empenho,
liquidação e pagamento. A ingestão segue o padrão de lotes do projeto, com preparação,
validação, ativação transacional, arquivamento da versão anterior e hash SHA-256 por
registro.

A inspeção revelou que o CSV denominado “2025” é consolidado: suas 10.976 linhas
abrangem 2020 a 2025. A carga seleciona o exercício explicitamente e registra 10.559
linhas descartadas por pertencerem a outros anos. A versão ativa de 2025 contém 417
registros, 43 autores, 3 funções, 271 beneficiários e 147 municípios conciliados.
Dezessete registros não foram associados territorialmente porque o campo também contém
órgãos ou outros rótulos que não correspondem a municípios.

Foram detectados 12 valores monetários `#N/D`. Para permitir agregação, esses valores
são convertidos tecnicamente para zero, mas sua quantidade permanece nas métricas e é
exibida na interface como limitação. O campo “Número PDF” foi exportado em notação
científica e apresentou apenas dois valores para milhares de linhas, evidenciando perda
de precisão; ele foi preservado como informação, mas excluído da identificação e da
deduplicação.

A narrativa separa rigorosamente indicado, empenhado, liquidado e pago. Os quatro
valores não são parcelas somáveis, mas estados distintos do processo. Gráficos por autor
e função são acompanhados de ressalvas: concentração de valor não demonstra mérito,
favorecimento ou irregularidade. A tabela detalhada oferece objeto e beneficiário para
que a leitura quantitativa seja contextualizada.

### Decisão sobre a fonte de Obras Públicas

Antes deste incremento foi investigado o Painel de Obras da SEINFRA, alimentado pelo
GOMAP. A fonte oficial oferece andamento, geolocalização, avanço físico, valores,
contratos e aditivos, mas somente por relatórios incorporados do Power BI. Como não foi
localizado arquivo aberto ou endpoint documentado, a extração do protocolo interno do
Power BI foi considerada incompatível com os requisitos de estabilidade,
reprodutibilidade e auditabilidade do TCC. A implementação foi adiada até a publicação
de uma fonte estruturada oficial.

## Incremento 15 — Drill-down municipal e comparação contextual

O mapa passou a funcionar como porta de entrada para um perfil municipal detalhado.
A requisição utiliza código IBGE e exercício, evitando identificar o território por
texto. O backend agrega os créditos de ICMS, IPVA e IPI, a dedução do Fundeb e a
série mensal, e calcula com funções de janela a posição absoluta e per capita sobre
o conjunto completo dos 246 municípios.

A apresentação segue uma sequência de três perguntas. Primeiro, cartões de composição
mostram a origem tributária e a participação percentual no total. Depois, colunas
empilhadas mostram a evolução mensal e preservam a contribuição de cada tributo. Por
fim, uma tabela compara o município selecionado aos cinco municípios com população
numericamente mais próxima, exibindo a diferença populacional, total e valor per
capita.

Inicialmente foi considerada uma faixa fixa de ±25% da população. A validação mostrou
que Goiânia não possuía qualquer par nessa faixa, o que eliminaria a comparação para
um caso central. O critério foi substituído pelos cinco vizinhos populacionais mais
próximos, acompanhado de diferença percentual explícita. A interface ressalta que
proximidade de população não significa equivalência econômica, tributária ou
administrativa.

## Incremento 14 — Visualização cartográfica municipal

O mapa municipal utiliza a malha oficial mais recente disponibilizada pela API de
Malhas Geográficas do IBGE. A resposta foi persistida no frontend como GeoJSON de
qualidade mínima, contendo 246 feições e o código municipal no atributo `codarea`.
Uma validação automática comparou esses códigos com a dimensão territorial da API e
confirmou cobertura integral, sem municípios ausentes.

Para evitar nova dependência e manter controle sobre a didática, a renderização foi
construída diretamente em SVG. O algoritmo percorre todas as coordenadas para calcular
os limites geográficos, ajusta escala e centralização ao espaço disponível e converte
anéis de geometrias `Polygon` e `MultiPolygon` em caminhos vetoriais. O mapa permanece
responsivo por meio de `viewBox`.

Os municípios são distribuídos em cinco classes quantílicas. Cada faixa reúne
aproximadamente 20% das localidades, o que torna visíveis padrões territoriais mesmo
quando Goiânia e outros grandes centros concentram valores muito superiores. Essa
escolha comunica posição relativa, não distância monetária absoluta; por isso a
legenda explicita a interpretação e o painel de detalhes apresenta os valores exatos.

Mapa e ranking compartilham o seletor de valor total ou per capita. A interação aceita
mouse, foco por teclado, Enter e barra de espaço, e cada território possui descrição
acessível. Ao selecionar um município são exibidos valor creditado, razão por habitante,
população estimada e código IBGE. A interface ressalta que a coloração não mede
qualidade administrativa nem prova eficiência ou irregularidade.

## Incremento 13 — Identidade territorial e análise per capita

A etapa territorial introduziu `municipios_ibge`, `populacoes_municipais` e
`aliases_municipios`. A primeira tabela utiliza o código IBGE como identidade estável;
a segunda preserva população, ano, data de referência e fonte; a terceira registra a
relação entre a grafia da base estadual e o município oficial, incluindo o método de
conciliação. Essa separação impede que uma correção de nome altere os fatos financeiros
originais.

A normalização automática remove apenas diferenças de caixa, acentuação, pontuação e
espaçamento. Dos 247 valores territoriais publicados, 245 foram associados por
igualdade normalizada. A auditoria mostrou que `BOM JESUS` correspondia ao único
município oficial ausente, Bom Jesus de Goiás, e o vínculo com o código 5203500 foi
registrado como manual. O valor `MUNICIPIO NAO INFORMADO` permaneceu sem associação.
O resultado final contém os 246 municípios de Goiás e 45 lançamentos sem município,
mantidos nos totais estaduais e excluídos dos rankings territoriais.

As estimativas populacionais de 2025 foram consultadas na API do IBGE e registradas
com referência em 1º de julho. A API calcula o total creditado dividido pela população
do mesmo município e exercício. Na interface, o cidadão pode alternar entre ranking
absoluto e per capita; uma ressalva explica que a razão não representa dinheiro pago
individualmente ao morador. No recorte de janeiro a julho de 2025, Goiânia lidera o
valor absoluto e Perolândia o valor por habitante, com aproximadamente R$ 3.893,77
para uma população estimada de 2.999 pessoas.

## Incremento 12 — Repasses aos municípios

O Radar Goiano passou a incorporar os repasses estaduais creditados aos municípios,
publicados pela Secretaria da Economia no Portal de Dados Abertos de Goiás. A carga
consulta o catálogo CKAN, seleciona os recursos mensais do exercício solicitado e
valida se o campo `ANO_MES_REPASSE` corresponde ao mês anunciado no recurso. Essa
verificação reduz o risco de associar um arquivo ao período incorreto apenas pelo
nome ou pela data de publicação.

Foi adotado um modelo versionado em duas tabelas. `lotes_repasses` registra a origem,
o período, o estado de preparação e a versão ativa; `fatos_repasses_municipais`
preserva datas, município e valores brutos, deduções do Fundeb e valores efetivamente
creditados de ICMS, IPI e IPVA. Cada linha recebe um hash determinístico, usado para
impedir duplicação dentro do lote. A nova versão somente se torna ativa depois das
validações de volume e cobertura mensal, em uma troca transacional que arquiva o lote
anterior sem apagá-lo.

A API agregadora fornece totais e série mensal, enquanto a nova tela organiza a
leitura em linguagem cidadã: valor total creditado, participação dos tributos,
dedução destinada ao Fundeb e ranking das maiores somas territoriais. A interface
explica que repasse creditado não representa todo o orçamento municipal e informa
explicitamente a cobertura parcial da fonte.

Na carga realizada para 2025, os sete recursos disponíveis, de janeiro a julho,
produziram 11.115 registros. Foram apurados R$ 3,62 bilhões creditados: R$ 3,35
bilhões de ICMS, R$ 250,69 milhões de IPVA e R$ 22,89 milhões de IPI. As deduções
informadas para o Fundeb somaram R$ 1,05 bilhão.

A fonte contém 247 grafias territoriais distintas, embora Goiás possua 246
municípios. Por integridade, a aplicação não fundiu nomes automaticamente e apresenta
o indicador como “nomes territoriais publicados”. A próxima etapa deverá confrontar
essas grafias com um cadastro municipal oficial versionado. Pelo mesmo motivo, a
comparação per capita foi adiada até que a dimensão territorial e a população do
mesmo ano de referência estejam integradas, evitando combinar períodos ou localidades
incompatíveis.

## 1. Finalidade do documento

Este memorial registra as decisões técnicas, métodos, resultados e limitações das funcionalidades implementadas no Radar Goiano. O conteúdo pode servir como base para os capítulos de metodologia, desenvolvimento, resultados e trabalhos futuros do TCC. As medições registradas foram realizadas no ambiente local de desenvolvimento e não devem ser generalizadas como benchmark de produção.

## 2. Abordagem metodológica

O desenvolvimento foi organizado em incrementos verticais. Cada incremento contempla banco de dados, API, interface, documentação e validação. Essa estratégia permite entregar uma capacidade analítica completa por vez e verificar o resultado com dados reais antes de avançar.

O fluxo adotado foi:

1. inspeção do esquema e da qualidade dos dados;
2. definição das métricas e limitações;
3. criação de consultas parametrizadas e paginadas;
4. indexação dos filtros mais frequentes;
5. integração com a interface;
6. testes automatizados e testes com o PostgreSQL real;
7. registro das decisões e resultados.

## 3. Base tecnológica

- PostgreSQL 18 para armazenamento e agregações;
- Python, FastAPI e SQLAlchemy no backend;
- React 19, Vite, Tailwind CSS e Recharts no frontend;
- JSON estático apenas para painéis agregados legados;
- variáveis de ambiente para credenciais e origens CORS.

A tabela `pagamentos_estaduais` contém 4.079.506 registros, entre 2003 e 2025. Por causa desse volume, a arquitetura foi alterada para executar filtros, somas e paginação no banco, transmitindo ao navegador somente os resultados necessários.

## 4. Preparação da infraestrutura

Antes das novas funcionalidades, foram realizados os seguintes ajustes:

- retirada da senha do PostgreSQL do código-fonte;
- configuração por `DATABASE_URL` em arquivo `.env` ignorado pelo Git;
- correção das rotas de cache da API;
- validação dos anos aceitos nas rotas;
- CORS configurável por ambiente;
- correção do cache de contratos para todos os anos;
- tratamento visual de falhas de carregamento;
- declaração da dependência `scikit-learn`;
- remoção de bytecode Python do versionamento;
- carga dos extratores em tabelas de preparação antes de substituir dados oficiais.

As tabelas de preparação reduzem o risco de indisponibilidade: se um arquivo falhar ou a carga resultar em zero registros, a tabela oficial é preservada.

## 5. Incremento 1 — Explorador de Despesas

### Problema

Os painéis iniciais exibiam totais e rankings, mas não permitiam investigar os registros que formavam esses valores. Também não seria viável publicar milhões de despesas em um único JSON.

### Solução

Foi criada uma API paginada com três operações:

- descoberta de anos, órgãos e funções disponíveis;
- resumo agregado com empenhado, liquidado, pago e saldo;
- listagem detalhada paginada.

A interface recebeu filtros por ano, mês, órgão, função e texto. A busca textual contempla credor, documento e número do empenho. A tabela retorna no máximo 100 registros por página; a interface utiliza 25.

### Segurança

Valores dos filtros são enviados ao SQL por parâmetros vinculados. As colunas de ordenação são selecionadas a partir de uma lista fechada, evitando que o usuário injete identificadores SQL.

### Desempenho observado

Foram criados índices para ano/mês, ano/órgão, ano/função e ano/valor pago. No ambiente local:

- consultas de 2025 responderam aproximadamente entre 0,24 e 0,39 segundo;
- o resumo dos 4.079.506 registros respondeu em aproximadamente 1,31 segundo.

### Limitações

- os valores são nominais;
- a qualidade depende dos campos publicados pela fonte;
- o saldo exibido é `liquidado - pago`, não uma previsão de caixa;
- registros atípicos não constituem evidência de irregularidade.

## 6. Incremento 2 — Perfil do Fornecedor

### Problema

O mesmo fornecedor pode aparecer em diversos órgãos, anos e contratos. Usar somente o nome produziria associações falsas devido a abreviações, erros e homônimos.

### Análise dos dados

Dos 4.079.506 pagamentos, cerca de 1,45 milhão possuem algum conteúdo no campo de documento. Foram encontrados documentos incompletos, códigos internos e valores em notação científica. Na tabela de contratos, 60.673 de 61.447 registros possuem algum documento.

### Decisão de identidade

A associação automática foi limitada a CNPJs:

- compostos somente por dígitos e pontuação documental;
- normalizados para 14 dígitos quando houve perda de zero à esquerda;
- aprovados pelo cálculo oficial dos dois dígitos verificadores.

CPF, nome e documento corrompido não são usados como chave. Essa escolha reduz cobertura, mas prioriza precisão e auditabilidade.

### Resultado

O perfil apresenta totais, número de órgãos, período observado, evolução anual, principais órgãos pagadores, variações de nome, contratos associados e pagamentos paginados. Dois índices funcionais foram criados sobre o CNPJ normalizado.

Em um CNPJ real da base, foram observados os seguintes tempos locais:

- resumo: aproximadamente 0,11 segundo;
- pagamentos: aproximadamente 0,02 segundo;
- contratos: aproximadamente 0,006 segundo.

### Limitações

- registros sem CNPJ válido não são relacionados;
- o perfil demonstra relacionamento financeiro, não irregularidade;
- o valor contratado não equivale necessariamente ao valor pago;
- a lista de contratos é limitada aos 100 registros mais recentes.

## 7. Incremento 3 — Comparador de Órgãos e Períodos

### Objetivo

Permitir a comparação de dois cenários independentes, cada um formado por um órgão e um exercício. Isso possibilita comparar órgãos no mesmo ano ou o mesmo órgão em anos diferentes.

### Indicadores

- total empenhado, liquidado e pago;
- quantidade de registros e credores;
- percentual pago sobre o empenhado;
- saldo liquidado ainda não pago;
- concentração do maior credor;
- execução mensal;
- funções com maior valor pago;
- principais credores.

### Cálculo da variação

A variação nominal do cenário B sobre o cenário A é calculada por:

```text
variação (%) = ((B - A) / |A|) × 100
```

Quando o valor do cenário A é zero, a variação é apresentada como indefinida, evitando divisão por zero e percentuais enganosos.

### Interpretação

Uma variação positiva não é classificada automaticamente como ruim. O aumento pode decorrer de expansão do serviço, inflação, mudança de competência, reorganização administrativa ou alteração da cobertura da base. A interface apresenta essa ressalva.

### Limitações

- comparação em valores nominais, ainda sem correção inflacionária;
- quantidade de credores é baseada no nome informado na fonte;
- concentração é calculada pelo maior nome de credor, podendo haver variações cadastrais;
- órgãos que mudaram de denominação exigirão uma futura dimensão de identidade organizacional.

### Qualidade dos nomes dos órgãos

Durante o teste do comparador, foram identificados caracteres de controle em 1.298.382 registros de `nome_orgao`. A base possui 347 nomes distintos tanto antes quanto depois da remoção desses caracteres, indicando ruído de representação, sem fusão observada de categorias.

O dado bruto foi preservado. A inspeção mostrou que os controles eram sintomas de bytes UTF-8 interpretados como Latin-1. Consultas e filtros recodificam somente as linhas que contêm esse marcador e preservam as demais. Um índice funcional combina ano e nome normalizado para evitar perda de desempenho. Essa abordagem mantém rastreabilidade e separa dado de origem de dado preparado para apresentação.

## 8. Incremento 4 — Orçamento e Receita

### Objetivo

Apresentar receita e despesa em uma visão conjunta, respeitando a diferença conceitual entre receita prevista, receita arrecadada, despesa empenhada, liquidada e paga.

### Cobertura da base

A tabela `receitas_estaduais` possui 311.635 registros, 294 órgãos e cobertura entre 2006 e 2025. Todas as linhas estão sem `data_arrecadacao`, mas possuem `mes_exercicio` válido; por isso, a série temporal utiliza ano e mês de exercício.

O preenchimento de `valor_previsto` não é uniforme. A cobertura observada inclui:

- 2025: 9,90%;
- 2024: 0%;
- 2023: 0,12%;
- 2021: 93,43%;
- 2020: 91,80%.

### Regra de confiabilidade

O percentual de receita arrecadada sobre a prevista somente é calculado quando pelo menos 70% dos registros do recorte possuem `valor_previsto > 0`. Abaixo desse limiar, o valor bruto é mostrado com alerta de cobertura, mas o percentual é omitido.

O limiar é uma regra conservadora do sistema, não uma norma contábil. Ele deve ser explicitado na metodologia e pode ser recalibrado após análise com o responsável pela fonte.

### Indicadores

- receita prevista e sua cobertura;
- receita arrecadada;
- percentual de realização quando confiável;
- despesa empenhada, liquidada e paga;
- série mensal integrada;
- categorias de receita;
- saldo financeiro observado.

O saldo financeiro observado é calculado por:

```text
saldo observado = receita arrecadada - despesa paga
```

Esse indicador não equivale ao resultado orçamentário ou fiscal oficial. As bases podem possuir escopos, momentos de atualização e classificações diferentes. Da mesma forma, despesa empenhada não representa dotação orçamentária.

### Decisões de interface

- alerta destacado quando a previsão possui baixa cobertura;
- ausência de percentual em vez de calcular um resultado enganoso;
- valores completos em tooltip e compactos nos indicadores;
- filtros por ano e mês;
- nota metodológica permanente na tela.

### Limitações

- ainda não existe dotação inicial e atualizada no esquema local;
- não há correção monetária;
- a data exata de arrecadação está ausente;
- previsão incompleta em exercícios recentes;
- o painel não substitui demonstrativos contábeis oficiais.

## 9. Incremento 5 — Central de Alertas Explicáveis

### Objetivo

Priorizar registros para revisão humana usando regras reproduzíveis e compreensíveis. O termo alerta significa ocorrência que atende a uma regra; não significa fraude, desperdício ou ilegalidade.

### Regra 1 — Duplicidade potencial

Agrupa registros com os mesmos órgão, favorecido, número de empenho, data de emissão e valor pago. Grupos com mais de um registro são apresentados para revisão.

Limitação: parcelas, retenções, desdobramentos e outros lançamentos contábeis legítimos podem compartilhar a mesma assinatura. Em 2025, a regra retornou 144.008 grupos, o que demonstra alta sensibilidade e necessidade de refinamento com identificadores contábeis adicionais.

### Regra 2 — Concentração em favorecido

Sinaliza quando um favorecido representa pelo menos 50% do valor pago por um órgão que:

- pagou no mínimo R$ 1 milhão no exercício;
- possui ao menos cinco favorecidos distintos.

Limitação: fornecedor exclusivo, concessionária, fundo público ou característica da política podem justificar concentração. A identidade ainda é agrupada pelo nome publicado nessa regra.

### Regra 3 — Crescimento mensal abrupto

Sinaliza crescimento de pelo menos 200% em relação ao mês imediatamente anterior, desde que:

- o mês anterior tenha ao menos R$ 1 milhão pagos;
- o mês atual alcance ao menos R$ 5 milhões.

Os pisos evitam percentuais muito altos produzidos por bases monetárias irrelevantes. Sazonalidade, repasses e encerramento do exercício continuam sendo explicações possíveis.

### Regra 4 — Pagamento atípico por IQR

Os pagamentos positivos são agrupados por função governamental. Para grupos com pelo menos 100 registros, calculam-se primeiro quartil (Q1), terceiro quartil (Q3) e intervalo interquartil:

```text
IQR = Q3 - Q1
limite superior = Q3 + 3 × IQR
```

Pagamentos acima do limite são classificados como estatisticamente atípicos. O multiplicador 3 é mais conservador que a regra exploratória usual de 1,5 IQR.

Limitação: distribuições de gastos públicos possuem caudas longas; um pagamento elevado pode ser esperado e legítimo. A função governamental é um grupo amplo e poderá ser refinada por natureza da despesa.

### API e interface

O endpoint `GET /api/alertas` recebe ano e tipo. Cada resposta contém regra, ressalva, total encontrado e no máximo 25 evidências. A interface consulta as quatro regras em paralelo, apresenta totais e usa painéis expansíveis para evitar sobrecarga visual.

Tempos locais observados para 2025 antes da paralelização no cliente:

- duplicidade: aproximadamente 2,53 segundos;
- concentração: aproximadamente 1,51 segundo;
- variação mensal: aproximadamente 0,65 segundo;
- IQR: aproximadamente 1,38 segundo;
- quatro regras sequenciais: aproximadamente 5,80 segundos.

Com as quatro requisições executadas em paralelo pela interface, o tempo total observado foi de aproximadamente 2,55 segundos, limitado principalmente pela regra de duplicidade.

### Interpretação e ética

As regras são mecanismos de triagem. A interface evita linguagem acusatória, não exibe CPF e apresenta a limitação junto de cada resultado. Uma conclusão exige consulta a empenhos, documentos, contratos, liquidações e contexto administrativo.

## 10. Incremento 6 — Rastreabilidade, Exportação e Qualidade

### Objetivo

Permitir que resultados sejam reproduzidos, compartilhados e analisados fora do sistema, ao mesmo tempo em que as limitações da fonte permanecem visíveis.

### Exportação filtrada

O Explorador de Despesas exporta os mesmos filtros aplicados na tela: ano, mês, órgão, função e busca. A consulta e a geração são realizadas no servidor em lotes de 500 linhas, evitando carregar todo o resultado na memória.

O arquivo usa UTF-8 com BOM e separador ponto e vírgula para facilitar a abertura em planilhas configuradas para o padrão brasileiro. O limite é de 10 mil linhas por arquivo, prevenindo exportações acidentais de milhões de registros.

### Segurança e minimização

Textos iniciados por `=`, `+`, `-` ou `@` recebem um apóstrofo antes de serem gravados. Essa medida reduz o risco de CSV Injection, no qual uma planilha interpreta conteúdo externo como fórmula.

Documentos com 11 dígitos são tratados como CPF e exportados mascarados. Documentos empresariais de 12 a 14 dígitos são normalizados como CNPJ. Conteúdos fora desses formatos são omitidos.

### URLs reproduzíveis

A aba, o ano, o mês, o órgão, a função, a busca e a página do Explorador são persistidos na query string. Assim, uma análise pode ser copiada e reaberta com o mesmo recorte, sem introduzir uma biblioteca de roteamento apenas para essa necessidade.

### Painel de qualidade e proveniência

O painel apresenta, para pagamentos, receitas, contratos, folha e diárias:

- quantidade de registros;
- intervalo de exercícios;
- maior data de referência disponível;
- percentuais de preenchimento de campos relevantes;
- link para a fonte oficial.

Completude mede presença, não correção semântica. Um campo preenchido ainda pode conter erros, valores padronizados incorretamente ou classificação inadequada.

Os indicadores são pré-calculados na tabela `metadados_qualidade`. A primeira implementação calculava agregações sobre todas as bases a cada requisição e ultrapassou 30 segundos no ambiente local. A materialização deslocou esse custo para uma rotina explícita de atualização: a carga inicial levou aproximadamente 28,5 segundos, enquanto a leitura do endpoint passou a 0,077 segundo. Após novas importações, os indicadores devem ser recalculados com `python atualizar_metadados.py`.

### Limitações de atualização

O sistema ainda não possui registros históricos da data em que as cargas anteriores foram executadas. Por isso, a maior data encontrada é chamada de data de referência e não de data de atualização. Registrar início, fim, fonte, quantidade e resultado de cada carga é trabalho futuro.

## 11. Incremento 7 — Histórico e Observabilidade das Cargas

### Problema

A data mais recente encontrada nos registros descreve a referência temporal do dado, mas não comprova quando o processo de extração foi executado. Sem um histórico operacional, falhas parciais, duração e quantidade processada dependiam apenas das mensagens do terminal.

### Solução implementada

A migração `007_historico_cargas.sql` cria uma tabela de auditoria com conjunto, fonte, estado, início, término, duração, quantidade final de registros e mensagem de erro. O estado possui restrição no banco e só aceita `em_execucao`, `sucesso` ou `falha`; registros finalizados precisam possuir horário de término.

O comando `python executar_carga.py <conjunto>` funciona como ponto central de execução. Uma lista fechada associa cada conjunto ao script, tabela oficial e fonte, impedindo que um nome recebido na linha de comando seja convertido em caminho ou identificador SQL arbitrário. O extrator continua sendo executado como processo separado, preservando seu comportamento e código de saída.

Em caso de sucesso, o executor conta os registros na tabela oficial, encerra a auditoria e recalcula os metadados materializados. Em caso de código de saída diferente de zero ou exceção, registra a falha e uma mensagem limitada a dois mil caracteres. A API `GET /api/cargas` permite consultar até cem execuções e o frontend apresenta as vinte mais recentes no painel de qualidade.

### Limitação histórica

O monitoramento é prospectivo. O sistema não cria registros retroativos para importações anteriores porque não há evidência suficiente para determinar início, duração ou resultado dessas execuções. Inicialmente, portanto, a tabela aparece vazia até a primeira carga realizada pelo novo executor.

Na validação do incremento, a migração foi aplicada ao PostgreSQL local, a API respondeu HTTP 200 com a coleção inicialmente vazia e a suíte passou de 15 para 17 testes. Os novos testes confirmam que conjuntos conhecidos são mapeados pela lista fechada e nomes arbitrários são rejeitados. O lint e o build de produção do frontend também foram concluídos com sucesso.

## 12. Incremento 8 — Auditoria da Base Analítica

Após a identificação de divergências entre planilhas, foi executada uma auditoria somente leitura sobre o PostgreSQL e uma comparação direta com recursos atuais do Portal de Dados Abertos de Goiás. O procedimento, resultados numéricos, limitações e plano de reconstrução estão registrados em `AUDITORIA_QUALIDADE_DADOS.md`.

A comparação de receitas de 2024 confirmou duplicação exata: 10.652 linhas no arquivo oficial atual e 21.304 no banco. Pagamentos apresentaram 2.108.944 linhas excedentes segundo uma chave heurística, mas a fonte atual de 2024 possui granularidade muito maior e um identificador oficial que o esquema local não preserva. Portanto, uma exclusão baseada apenas em `DISTINCT` foi rejeitada por risco de remover pagamentos legítimos.

### Normalização dos nomes nos caches

Foi criada a rotina idempotente `corrigir_nomes_json.py` para manter sincronizados os caches do backend e do frontend. Ela corrige somente sequências com evidência de UTF-8 interpretado como Latin-1 e formata campos explicitamente identificados como nomes. Textos já mistos permanecem inalterados; conectivos ficam em minúsculas e siglas ou sufixos societários são preservados. A gravação usa arquivo temporário e substituição atômica, reduzindo o risco de deixar JSON parcialmente escrito. Na execução inicial, 121 arquivos foram analisados nas duas pastas, 109 cópias foram atualizadas e os 61 JSON públicos foram novamente validados.

Também foi constatado que o catálogo oferece fatos distintos para empenhos, liquidações e pagamentos. Essa descoberta altera a modelagem proposta: as etapas da execução da despesa devem permanecer separadas, em vez de preencher uma única linha a partir do arquivo de pagamentos. Como contenção, as cargas legadas de pagamentos e receitas foram bloqueadas e a interface passou a informar que os indicadores estão sob auditoria.

### Reconstrução em camadas versionadas

A migração `008_camadas_financeiras_versionadas.sql` criou as tabelas `fatos_empenhos`, `fatos_liquidacoes`, `fatos_pagamentos` e `fatos_receitas`, separadas conforme o achado da auditoria, além de `versoes_dados` (um lote de carga) e `recursos_ingestao` (proveniência de cada arquivo: URL, identificador CKAN, data de modificação e hash SHA-256). A migração `009_ano_exercicio_fatos.sql` acrescentou `ano_exercicio`, distinguindo o ano do movimento do exercício orçamentário informado pela fonte.

`backend/carga_financeira_versionada.py` carrega uma versão isolada sem alterar as tabelas legadas, selecionando apenas recursos anuais independentes e mensais do ano corrente, excluindo consolidados sobrepostos. Cada linha recebe uma `chave_conteudo` (hash SHA-256 de todos os campos), usada para detectar sobreposição entre recursos. A validação bloqueante (`validar_versao`) rejeita a versão — marcando-a como `rejeitada` — se houver zero registros, mês fora de 1–12, ano fora de `[1990, ano atual]`, soma absoluta nula, sobreposição de conteúdo entre recursos ou exercício divergente do parâmetro informado.

A primeira execução completa, em 28 de agosto de 2026, produziu a versão 10, validada com 1.289.486 empenhos, 2.948.640 liquidações, 2.819.715 pagamentos (cobertura 2003–2026) e 160.329 receitas (cobertura 2006–2025), sem sobreposição de conteúdo entre recursos e sem meses ou anos inválidos.

Limitação: a validação é interna à própria carga (consistência, cobertura, ausência de sobreposição); não é, por si só, uma comparação linha a linha com o arquivo oficial.

### Ativação de versão

Uma versão `validada` ficava isolada até este ponto — nenhuma rota ou tela a consumia, e não havia mecanismo para promovê-la a fonte oficial sem apagar dados. O script `backend/ativar_versao.py` resolve essa lacuna com três operações: `--ativar`, `--reverter` e `--listar`.

Antes de ativar, `verificar_estabilidade_fonte()` reconsulta o catálogo oficial para cada recurso já baixado daquela versão. Um recurso removido do catálogo bloqueia a ativação (contornável com `--ignorar-divergencias`); uma data de modificação diferente da registrada no download gera apenas um aviso, pois recursos do exercício corrente são legitimamente atualizados pela fonte ao longo do ano. A troca de status ocorre em uma única transação: a versão hoje `ativa` (se houver) passa para `arquivada` e a versão alvo passa para `ativa`. Um índice único parcial (`idx_uma_versao_ativa`, migração 008) garante no banco que nunca existam duas versões ativas simultaneamente. `--reverter` aplica a mesma transação no sentido inverso, promovendo uma versão `arquivada` de volta a `ativa`; nenhum dado é apagado em nenhum dos dois sentidos, apenas o status muda.

Cada ativação ou reversão é registrada como uma linha em `historico_cargas` (conjunto `ativacao_versao`), reaproveitando a tabela e o endpoint `GET /api/cargas` já existentes do Incremento 7 — o painel de Qualidade dos Dados passa a listar essas trocas sem nenhuma alteração de frontend. As métricas de estabilidade da fonte ficam anexadas ao campo `metricas` da versão em `versoes_dados`.

Correção durante a validação: a primeira execução comparou datas de modificação usando `str(datetime)`, que separa data e hora com espaço, contra o formato ISO 8601 (separador `T`) devolvido pelo catálogo — os 119 recursos da versão foram sinalizados incorretamente como "modificados após o download". A comparação foi corrigida para usar `isoformat()`; a nova verificação confirmou 0 divergências e 0 avisos reais, validando que a fonte permaneceu estável desde o download original. A versão 10 foi então ativada: `vw_pagamentos_ativos` e `vw_empenhos_ativos` passaram a retornar, respectivamente, 2.819.715 e 1.289.486 registros.

Esta limitação foi superada posteriormente: a versão 11 foi revertida para a versão 10 e, em seguida, restaurada, conforme registrado no fechamento deste incremento.

### Migração das rotas para a camada versionada

Antes de trocar o consumo das telas, dois achados mudaram o escopo da migração:

Primeiro, o campo `funcao` da tabela legada `pagamentos_estaduais` — usado pelo filtro do Explorador de Despesas, pelo agrupamento da Central de Alertas (Regra 4) e pelo painel "Funções com maior pagamento" do Comparador — está **0% preenchido em produção**: 0 de 4.079.506 registros. O extrator legado (`extracao_de_gastos.py`) lê `NOMEFUNCAO`/`FUNCAO` do arquivo consolidado, mas essas colunas não existem no arquivo atual (confirmado baixando `Empenhos - 2003` e inspecionando o cabeçalho: `SALDO_EMPENHADO;RAZAO_SOCIAL_CREDOR;DATA_EMPENHO;NUMR_ANO;NUM_MES;DOTACAO;NOME_ORGAO;CODG_ORGAO;CPF_CNPJ;NUMR_EMPENHO;NUMR_PROCESSO_EMPENHO;DESCRICAO_EMPENHO`). O campo `DOTACAO` é um identificador curto (1 a 3 dígitos), não um código composto decomponível em função/subfunção. Ou seja, a função nunca esteve disponível em produção: o dropdown já carregava vazio e a Regra 4 já calculava o IQR sobre um único grupo ("Não informada"), não por função como a documentação registrava.

Segundo, `valor_empenhado` e `valor_liquidado` na mesma tabela legada estão **sempre zero** — `extracao_de_gastos.py:86-87` os define como `0` incondicionalmente, porque o extrator lê apenas o arquivo de pagamentos. Todo KPI "Empenhado"/"Liquidado" exibido nas telas era, portanto, sempre R$ 0,00.

Com base nesses dois achados, os cinco controllers que liam `pagamentos_estaduais`/`receitas_estaduais` foram migrados para `vw_pagamentos_ativos`, `vw_empenhos_ativos`, `vw_liquidacoes_ativas` e `vw_receitas_ativas` (a versão ativa das tabelas `fatos_*`):

- **Explorador de Despesas** (`rotas_despesas.py`): KPIs de empenhado/liquidado/pago calculados como três somas independentes (uma consulta por fato, filtradas pelos mesmos critérios de ano/mês/órgão/busca), em vez de três colunas de uma única linha — coerente com a separação de fatos definida na auditoria. O filtro e a coluna de função foram removidos das telas. A listagem detalhada, por linha de pagamento, perdeu as colunas empenhado/liquidado (não existem no grão de um pagamento nas novas tabelas) e passou a mostrar apenas o valor pago.
- **Central de Alertas** (`rotas_alertas.py`): a Regra 4 (atípicos por IQR) passou a agrupar por órgão em vez de função — o título mudou de "Pagamentos atípicos na função" para "Pagamentos atípicos por órgão".
- **Comparador de Órgãos** (`rotas_comparacoes.py`): o painel "Funções com maior pagamento" foi substituído por "Principais credores" (já calculado, mas não exibido, na versão anterior).
- **Orçamento e Receita** (`rotas_fiscal.py`): mesma decomposição em três somas independentes por fato; a granularidade de categoria de receita mudou de `categoria_receita`/`origem_receita` (dois campos) para `categoria_economica` (mais granular na fonte atual).
- **Perfil do Fornecedor** (`rotas_fornecedores.py`): mesma decomposição por fato, sempre filtrando por `documento_credor`. Como esse campo é gravado com pontuação na fonte atual (`"01.409.705/0001-20"`, não 14 dígitos), foi criada a expressão `DOCUMENTO_CREDOR_NORMALIZADO` em `sql_utils.py`, com índices funcionais dedicados (migração `010_indices_fatos_consulta.sql`) para preservar o tempo de resposta.

Verificação: suíte de 22 testes ajustada e aprovada; os 16 endpoints migrados foram exercitados via HTTP contra o PostgreSQL real (não apenas TestClient), com resultados agora coerentes — por exemplo, o resumo de 2025 passou a mostrar R$ 47,28 bi empenhados e R$ 46,29 bi liquidados, valores reais em vez de R$ 0,00. `npm run lint` e `npm run build` (Vite) concluídos sem erros. A interface foi verificada visualmente com Playwright headless contra o backend e o PostgreSQL reais: nenhum erro de console, filtro de função ausente, e telas de Despesas, Comparador, Fiscal, Alertas e Perfil do Fornecedor renderizando dados reais.

**Bug de codificação descoberto na verificação visual**: 109 dos 335 nomes de órgão distintos em `fatos_pagamentos` (32.937 linhas) apareciam como mojibake (ex.: `agência` como `agÃªncia`). A causa raiz estava em `carga_financeira_versionada.py`: a detecção de codificação decodificava apenas os primeiros 64 KB de cada arquivo como UTF-8 e, ao encontrar qualquer byte inválido nessa amostra, descartava UTF-8 para o **arquivo inteiro** e o relia como Latin-1 — corrompendo acentos que eram UTF-8 válido. A correção (`detectar_codificacao`, com `encoding_errors="replace"` no `pd.read_csv`) só recai para Latin-1 quando a taxa de bytes inválidos ao decodificar como UTF-8 é significativa (≥ 0,1%); caso contrário, usa UTF-8 e substitui os poucos bytes realmente inválidos por `�`, preservando o restante do arquivo.

Uma nova carga completa (versão 11, iniciada às 14:23 e concluída às 14:49 de 28 de agosto de 2026) foi executada e ativada no mesmo dia. Os totais de registros permaneceram idênticos aos da versão 10 (1.289.486 empenhos, 2.948.640 liquidações, 2.819.715 pagamentos, 160.329 receitas), confirmando que a correção não alterou volume nem introduziu perda de dados — apenas a decodificação de texto mudou. A contagem de nomes de órgão distintos em pagamentos caiu de 335 para 222, porque grafias corrompidas e corretas do mesmo órgão (ex.: `agência` e `agÃªncia`) se fundiram em uma única forma. A verificação da string bruta em bytes (`ag\xc3\xaancia`, UTF-8 válido para "agência") e a checagem visual no navegador confirmaram a correção; ferramentas de terminal usadas durante a investigação mostraram mojibake de exibição próprio do console em alguns pontos, o que exigiu confirmar a codificação a partir dos bytes brutos da resposta, não da tela do terminal. Pequenas diferenças de totais entre as versões 10 e 11 (ex.: pago passou de R$ 44,37 bi para R$ 46,69 bi em 2025) refletem publicações novas no catálogo oficial entre os dois horários de carga, e não um efeito da correção de codificação.

### Fechamento das pendências do incremento

Três pendências registradas ao final da migração de rotas foram resolvidas na sequência:

A migração `011_metadados_qualidade_versionada.sql` reescreveu `atualizar_metadados_qualidade()` para que os conjuntos `pagamentos` e `receitas` do painel de Qualidade dos Dados passem a refletir `vw_pagamentos_ativos`/`vw_receitas_ativas`, em vez das tabelas legadas. Como `fatos_receitas` não tem `ano_exercicio` nem `valor_arrecadado`/`data_arrecadacao` (o exercício é o próprio campo `ano`; o valor chama-se `valor_realizado`; não há data), as métricas de qualidade de receitas foram redesenhadas: `previsao_positiva_pct` permanece, `arrecadacao_preenchida_pct` e `data_preenchida_pct` foram removidas (deixaram de fazer sentido, já que os campos correspondentes agora têm restrição `NOT NULL` ou não existem) e `categoria_preenchida_pct` foi adicionada. `ativar_versao.py` passou a chamar essa função dentro da mesma transação de ativação/reversão, para que o painel nunca fique defasado da versão ativa. Após a migração, o conjunto `pagamentos` do painel passou a mostrar 2.819.715 registros (o volume real servido pela aplicação) em vez dos 4.079.506 da tabela legada, e a maior data de referência passou de ausente para `2026-07-31` (antes a legada usava `data_emissao`, que não corresponde ao pagamento).

`--reverter` foi exercitado de fato, não apenas lido: a versão 11 foi revertida para a 10 (a contagem de órgãos distintos em `/api/despesas/filtros?ano=2025` voltou de 67 para 103, confirmando que o mojibake da versão 10 reapareceu) e então revertida de volta para a 11 (voltou a 67), restaurando o estado limpo. Isso confirma que as views `vw_*_ativos` refletem a versão ativa dinamicamente, sem exigir reinício do servidor. No histórico de cargas, essas duas reversões levaram aproximadamente 42 segundos cada, contra 0,013 segundo da ativação original da versão 11 — a diferença é o próprio `atualizar_metadados_qualidade()` (adicionado nesta etapa), que passou a rodar dentro da transação de troca de versão.

O exercício também expôs um defeito visual no painel de Qualidade dos Dados: a coluna "Fonte" da tabela de histórico de cargas sempre renderizava um link `<a href={carga.fonte}>`, presumindo que `fonte` fosse sempre uma URL — válido para os conjuntos legados (`executar_carga.py`), mas não para as linhas de `ativacao_versao`, cuja `fonte` é uma descrição textual (ex.: "ativação da versão 11 via ativar_versao.py"). O componente `QualidadeDados.jsx` passou a renderizar o link apenas quando `fonte` começa com `http`, e a exibir o texto simples caso contrário; o nome do conjunto na tabela também passou a trocar `_` por espaço antes de exibir.

`backend/tests/test_integracao_endpoints.py` (novo) usa `TestClient` do FastAPI contra o PostgreSQL real (não `sqlite://`), cobrindo os cinco controllers migrados com oito testes, dois deles testes de regressão explícitos para os bugs corrigidos nesta etapa: `kpis.empenhado`/`kpis.liquidado` maiores que zero em `/api/despesas/resumo`, e ausência da chave `funcoes` em `/api/despesas/filtros`. A classe de teste se autodesativa (`unittest.skipUnless`) quando não há PostgreSQL real com uma versão `ativa`, para não quebrar a suíte em um ambiente sem banco. A suíte cresceu de 22 para 30 testes; a execução completa passou de milissegundos para aproximadamente 70 segundos, porque os testes de integração consultam tabelas de milhões de linhas — uma troca aceitável para uma suíte executada sob demanda.

## 13. Validação e qualidade

As verificações usadas no projeto incluem:

- compilação sintática dos módulos Python;
- testes unitários de ano, filtros parametrizados e CNPJ;
- testes dos endpoints com `TestClient`;
- consultas contra o PostgreSQL local;
- ESLint do frontend;
- build de produção com Vite;
- validação sintática dos caches JSON;
- `git diff --check` para problemas de formatação.

Ao final do sexto incremento, 15 testes automatizados foram executados com sucesso. Em uma verificação funcional local, a exportação de cinco registros levou aproximadamente 0,164 segundo e o endpoint materializado de metadados levou 0,077 segundo. Esses valores são registros do ambiente de desenvolvimento, não um benchmark de produção.

Após a reconstrução e ativação de versão descritas no Incremento 8, a suíte passou a incluir testes unitários, testes de integração via `TestClient` contra o PostgreSQL real e testes específicos das regras de ativação e reversão. A verificação da interface também deixou de depender somente de inspeção manual com a inclusão da suíte Playwright descrita no Incremento 9.

## 13.1 Incremento 9 — Operação reproduzível e testes end-to-end

O frontend recebeu uma suíte Playwright executada em Microsoft Edge local. O cenário percorre as nove áreas do Radar Goiano, falha se houver erro JavaScript, requisição de rede interrompida ou estado visual de erro, e verifica a persistência da aba e do exercício na URL após recarregar a página. Essa abordagem transforma a verificação visual anteriormente manual em um procedimento repetível.

Foram adicionados quatro testes unitários para `ativar_versao.py`: normalização de timestamps, bloqueio diante de recurso removido, ativação deliberada com divergência e exigência do status `arquivada` para reversão. Os testes isolam efeitos externos por mocks; a troca transacional real continua coberta pelo exercício documentado de reversão 11 → 10 → 11.

A operação local foi consolidada em dois scripts PowerShell. `scripts/radar.ps1` inicia apenas os serviços inativos, mantém logs fora do versionamento e valida API, documentação OpenAPI e frontend por HTTP. `scripts/atualizar_caches.ps1` exige uma seleção explícita de período e, após gerar os caches, valida a sintaxe JSON e a igualdade entre backend e frontend. A automação reduz variações entre execuções manuais sem ocultar operações destrutivas ou ativar versões de dados implicitamente.

Na validação de 31 de agosto de 2026, os 36 testes Python foram aprovados em aproximadamente 59 segundos, os dois cenários Playwright passaram em aproximadamente 13 segundos, e `npm run lint` e `npm run build` terminaram sem erros. O wrapper de cache também foi exercitado com 2026, confirmando geração, validade sintática e sincronização das quatro cópias JSON. Durante o teste do inicializador foi corrigido um detalhe da sondagem TCP: `TcpClient.EndConnect()` não retorna booleano, portanto o sucesso precisa ser confirmado antes de retornar explicitamente `$true`; o PostgreSQL também recebeu até três tentativas espaçadas para tolerar a liberação transitória da porta no Windows.

## 13.2 Incremento 10 — Storytelling para comunicação cidadã

A Visão Geral original privilegiava a densidade de indicadores. Ela somava folha, contratos e diárias sob o rótulo “custo total auditado” e representava a participação dessas parcelas como “distribuição do orçamento”. Essa operação era matematicamente possível, mas semanticamente inadequada: remuneração e diária são registros de execução, enquanto um contrato representa valor formalizado, pode abranger vários exercícios e não comprova pagamento integral. A visualização poderia, portanto, levar o público a interpretar grandezas heterogêneas como o gasto total do governo.

O redesenho adotou divulgação progressiva e alfabetização de dados. O “Resumo Cidadão” começa declarando alcance e limitações, apresenta os três conjuntos em cartões independentes, explica a concentração de folha e diárias por órgão, caracteriza os maiores registros como pontos que exigem contexto e termina oferecendo caminhos para investigar os dados detalhados. Um glossário diferencia empenho, liquidação e pagamento. Textos próximos aos gráficos explicam efeitos de porte institucional, previdência e cobertura, reduzindo inferências causais indevidas.

A linguagem também foi revisada. “Empresa favorita” foi removida; alertas são descritos como seleção analítica para revisão humana; e a Folha deixou de afirmar que um `IsolationForest` processou contracheques, porque o gerador atual utiliza rankings determinísticos e explicáveis. O layout mantém acesso às telas analíticas, mas organiza a entrada em quatro perguntas: o que está incluído, onde se concentra, o que merece contexto e como investigar.

Critérios automatizados foram adicionados ao Playwright: presença da explicação de que os conjuntos não formam o gasto total, ausência do rótulo antigo e renderização das novas etapas narrativas. Após a mudança, os dois cenários E2E, o ESLint e o build de produção foram aprovados. O Vite emitiu apenas o aviso não bloqueante de bundle JavaScript superior a 500 kB, indicando oportunidade futura de divisão de código por tela.

### Expansão da metodologia para todas as telas

Para evitar que a didática ficasse restrita à página inicial, foi criado o componente compartilhado `ContextoTela`. Ele estabelece uma abertura editorial uniforme com cinco elementos: domínio temático, título, descrição em linguagem direta, pergunta cidadã respondida e ressalva interpretativa. O componente foi aplicado ao Explorador de Despesas, Comparador, painel Fiscal, Central de Alertas, Qualidade dos Dados, Contratos, Folha, Diárias e Perfil do Fornecedor.

As ressalvas foram especializadas por domínio. O Explorador diferencia as etapas orçamentárias e o grão do pagamento; o Comparador destaca inflação, porte e atribuições; o Fiscal informa a dependência da cobertura; Alertas distingue ocorrência de regra de caso comprovado; Qualidade separa completude de exatidão; Contratos diferencia formalização de pagamento; Folha diferencia registros de pessoas distintas; Diárias exige contexto de duração e missão; e o Perfil do Fornecedor explicita a associação por CNPJ e a diferença entre contrato e pagamento.

O Playwright foi ampliado para exigir, em cada tela principal, a presença da pergunta orientadora e da instrução de interpretação. ESLint, build e os dois cenários E2E foram novamente aprovados em 31 de agosto de 2026. A pesquisa de expansão utilizou fontes oficiais do Portal de Dados Abertos, Portal da Transparência e Instituto Mauro Borges e originou `docs/ROADMAP_DADOS_RELEVANTES.md`, priorizando execução por função/natureza, repasses municipais, obras, emendas, instrumentos contratuais, convênios, sanções e indicadores territoriais.

### Correção de integração local

Durante a validação pelo navegador, as novas telas apresentaram `Failed to fetch`. A API autorizava a origem `http://localhost:5173`, enquanto o frontend havia sido aberto como `http://127.0.0.1:5173`. Embora ambos apontem para a máquina local, são origens distintas para a política de segurança do navegador. A configuração CORS foi ajustada para autorizar explicitamente os dois endereços no ambiente de desenvolvimento. A correção foi confirmada por requisições reais e por preflight `OPTIONS`, com o cabeçalho `Access-Control-Allow-Origin` correspondente à origem solicitante.

## 14. Cuidados éticos e de comunicação

O sistema trabalha com dados públicos, mas evita transformar anomalia estatística em acusação. Termos como “atípico”, “concentração” e “variação” devem ser acompanhados de metodologia e contexto. O sistema não conclui fraude, desperdício ou ilegalidade; ele organiza evidências para investigação humana.

O perfil detalhado foi limitado a pessoas jurídicas. Essa decisão minimiza a exposição desnecessária de pessoas físicas e reduz ambiguidades de CPF.

## 15. Trabalhos futuros

- correção monetária por índice oficial versionado;
- dimensão histórica de órgãos e fornecedores;
- comparação per capita;
- orçamento previsto versus realizado;
- inclusão dos metadados de proveniência dentro dos próprios arquivos exportados;
- captura estruturada de métricas por arquivo e quantidade de linhas rejeitadas;
- ampliação das regras de alerta e avaliação de falsos positivos;
- testes end-to-end da interface;
- decomposição de `dotacao` em função/subfunção, caso a fonte volte a publicar essa classificação — hoje o campo é apenas um identificador curto, sem estrutura decomponível.
# Geração incremental dos caches JSON (28/08/2026)

O gerador anterior carregava grandes amostras das tabelas em `DataFrame` e aplicava
`IsolationForest` localmente. Na folha de pagamento, com dezenas de milhões de
registros, essa estratégia elevava o consumo de memória e podia tornar a estação
indisponível.

O arquivo `backend/gerar_cache.py` foi reestruturado segundo uma arquitetura de
processamento *push-down*: somas, médias, contagens, máximos e rankings são calculados
pelo PostgreSQL, enquanto o Python recebe apenas os poucos registros que compõem o
JSON. Foram removidas as dependências de `pandas` e `scikit-learn` desse fluxo.

Controles operacionais adicionados:

- geração incremental de um exercício por vez com `--ano`;
- seleção explícita do consolidado e proteção contra execução completa acidental;
- `work_mem` de 16 MB por operação e apenas um trabalhador paralelo por consulta;
- tempo máximo configurável por consulta;
- parâmetros SQL vinculados para o ano, sem interpolação do valor informado;
- gravação atômica com arquivo temporário, `fsync` e substituição final;
- publicação independente e consistente no backend e no diretório público do frontend;
- alertas determinísticos e explicáveis baseados nos maiores valores individuais,
  apresentados como indícios que exigem validação documental, e não como prova de
  irregularidade.

Comandos operacionais:

```powershell
# Recomendado: somente o exercício que recebeu dados novos
python backend/gerar_cache.py --ano 2025

# Consolidado de todos os exercícios
python backend/gerar_cache.py --consolidado

# Regeneração histórica, sequencial e deliberada
python backend/gerar_cache.py --todos-os-anos --ano-final 2026
```

Na validação controlada do exercício de 2026, os quatro arquivos foram gerados e
publicados com sucesso, sem materializar a tabela de folha na memória do Python.

Como complemento, foi criada a migration
`012_indices_cache_por_exercicio.sql`. Ela adiciona índices B-tree sobre
`ano_exercicio` em contratos, folha e diárias. A criação utiliza
`CREATE INDEX CONCURRENTLY`, evitando bloqueios prolongados nas operações normais
das tabelas, e termina atualizando as estatísticas do planejador com `ANALYZE`.

Os índices foram aplicados e validados no PostgreSQL. O índice da folha ocupa
aproximadamente 344 MB e o planejador passou a utilizar `Index Only Scan` nas
consultas filtradas por exercício. No ensaio comparável do cache de 2026, o tempo
total caiu de aproximadamente 103 segundos para 1,4 segundo, uma redução próxima
de 98,6%. O resultado mais expressivo ocorre em exercícios sem registros ou muito
seletivos; anos com grande volume ainda demandam o processamento das linhas daquele
período, mas deixam de exigir a leitura integral dos 52 milhões de registros.

## 16. Incremento 17 — Perfil do Governador

### Problema/Objetivo

O roadmap de autoridades públicas (deputados, senadores, vereadores e Governador) foi avaliado por viabilidade de fonte antes de qualquer implementação. Deputados federais e senadores têm fontes maduras (CEAP da Câmara, CEAPS do Senado); deputados estaduais dependem de confirmação manual do portal da Alego; vereadores não têm fonte estruturada confiável nas 246 câmaras municipais de Goiás — mesmo padrão de bloqueio já registrado para Obras públicas no Incremento 16. O Governador foi o único caso com dado já presente na base local (folha de pagamento e diárias estaduais), sem exigir nova ingestão, e foi o escolhido para esta primeira entrega.

### Solução

O endpoint `GET /api/governador/resumo` (`backend/controllers/rotas_governador.py`) consulta `folha_pagamento` pelo cargo `Governador do Estado` e sua grafia atual `Governador - DSE-1` (o rótulo do cargo mudou em 2020 para a mesma função), retornando a série mensal completa, KPIs acumulados e os mandatos identificados por transição de nome na própria série. Diárias da estrutura da Governadoria são somadas por ano a partir de `diarias_passagens`, filtrando por cargo (`ILIKE '%governador%'`, excluindo `vice`). O frontend (`PerfilGovernador.jsx`) apresenta a série em gráfico de linha com referência ao teto constitucional, a tabela de mandatos e o gráfico de diárias por ano, seguindo o mesmo componente `ContextoTela` das demais telas.

Durante a implementação, a consulta de `evolucao_mensal` revelou que `folha_pagamento` publica linhas clones exatas (mesmo id diferente, todos os demais campos idênticos) para o cargo de Governador em 151 dos 165 meses — o mesmo padrão de duplicação já documentado em `docs/AUDITORIA_QUALIDADE_DADOS.md` para pagamentos e receitas, aqui confirmado também na folha. A consulta usa `SELECT DISTINCT` para eliminar os clones antes de somar; sem essa correção, a remuneração acumulada apareceria dobrada.

### Desempenho observado

A primeira medição da consulta por cargo, sem índice de apoio sobre 52 milhões de linhas de `folha_pagamento`, levou aproximadamente 39 segundos — inaceitável para uma tela interativa, e reproduzido tanto por `curl` direto quanto por uma verificação real no navegador (Playwright/Edge), onde a aba ficava presa no carregamento. A migração `017_indice_cargo_folha.sql` criou `idx_folha_cargo_lower` (`CREATE INDEX CONCURRENTLY` sobre `LOWER(cargo)`); após a criação, a mesma consulta passou a responder em aproximadamente 0,8 segundo.

### Limitações

O Governador não possui lançamentos individuais de diária na fonte oficial; os valores de diárias apresentados pertencem a cargos da estrutura da Governadoria (gabinete, ajudância de ordens, segurança), não ao titular do cargo pessoalmente — a tela e a resposta da API declaram essa distinção explicitamente para não sugerir viagens pessoais inexistentes na fonte. A identificação de mandatos é derivada da série mensal da folha, não de um cadastro eleitoral; substituições de curtíssima duração (ex.: abril de 2018, um único mês) aparecem como mandatos completos na tabela. A cobertura parlamentar é tratada nos incrementos seguintes.

## 17. Incremento 18 — Cota parlamentar de deputados federais e senadores

### Problema/Objetivo

Sequência do Incremento 17: depois do Governador, o pedido passou a ser deputados e senadores, na mesma tela, com o gasto separável por cargo. A pesquisa de viabilidade já registrada no roadmap havia identificado CEAP (Câmara) e CEAPS (Senado) como fontes maduras; faltava confirmar os endpoints exatos e implementar.

### Solução

Dois carregadores versionados (`backend/carga_deputados.py`, `backend/carga_senadores.py`) por exercício, seguindo o modelo de lote/fato já usado em Emendas e Repasses, com uma adaptação: o índice de lote ativo é único por `(status, ano)` em vez de por tabela inteira (`migrations/018_despesas_parlamentares.sql`), para permitir vários exercícios ativos simultaneamente — necessário porque esta tela mostra série histórica, diferente de Emendas/Repasses, que até aqui carregaram um único exercício cada.

Deputados federais usam o arquivo consolidado anual da Câmara (`camara.leg.br/cotas/Ano-AAAA.csv.zip`), filtrado por `sgUF = 'GO'` e identificado por `ideCadastro`. A versão integrada da carga dos senadores usa o CSV administrativo oficial (`adm.senado.gov.br/adm-dadosabertos/api/v1/senadores/despesas_ceaps/AAAA/csv`), concilia os nomes com a lista oficial da legislatura e persiste o identificador `COD_SENADOR`.

O endpoint por deputado/documento da API da Câmara (`/api/v2/deputados/{id}/despesas`) respondia `200` com lista vazia e cabeçalho `retry-after: 30` de forma consistente, mesmo após aguardar o tempo indicado e trocar de parlamentar/ano — sinal de limitação do lado do serviço, não do parâmetro. O arquivo consolidado anual (mesma fonte, outro formato de distribuição) não apresentou esse problema e evita 17 a 27 requisições por exercício; a implementação usa exclusivamente essa via.

Durante a implementação, o arquivo de deputados revelou dois identificadores numéricos distintos para o mesmo parlamentar: `ideCadastro` (usado pela API atual `dadosabertos.camara.leg.br/api/v2/deputados`, confirmado por amostragem cruzada) e `nuDeputadoId` (um identificador diferente, de origem não documentada no arquivo). A carga usa `ideCadastro` deliberadamente, para manter compatibilidade com o identificador público da API.

### Segurança

Todas as consultas usam parâmetros SQL vinculados (`ano`). A rota não aceita texto livre do cliente — `ano` é validado pelo FastAPI como inteiro antes de chegar à consulta.

### Desempenho observado

Cada carga anual de deputados baixa um arquivo nacional (~7,5 MB comprimidos, ~330 mil linhas) e filtra ~4 a 5 mil linhas de Goiás localmente; as oito cargas de 2019 a 2026 completaram em poucos segundos cada. As cargas de senadores são menores (11 a 21 mil linhas nacionais, 46 a 334 linhas de Goiás por ano).

### Limitações

A conciliação inicial do senador ainda depende do nome publicado nas duas fontes, mas o fato persistido usa o identificador oficial `COD_SENADOR`. Ausência em um exercício significa somente que nenhum documento foi encontrado na CEAPS consultada; não autoriza inferir gasto igual a zero. Deputados estaduais (Alego) e vereadores permanecem fora desta entrega — ver `docs/ROADMAP_DADOS_RELEVANTES.md` para a avaliação de viabilidade de cada um.

## 18. Incremento 19 — indicadores comparativos de despesas parlamentares

O incremento seguinte transformou o ranking simples em uma ferramenta de triagem explicável. A unidade de comparação é o parlamentar dentro do mesmo cargo e exercício. A média mensal considera somente meses com registros, reduzindo a distorção de mandatos parciais; o painel também apresenta total, documentos, glosas, pico mensal, categoria principal e concentração nessa categoria.

A regra de sinalização usa a mediana, mais resistente a valores extremos do que a média. Um caso recebe o rótulo “acima da mediana” apenas quando sua média mensal é pelo menos 25% maior que a mediana e existem dez ou mais pessoas na coorte. O rótulo direciona a consulta de notas e justificativas, mas não constitui diagnóstico de gasto excessivo ou ilícito. Como Goiás tem apenas três vagas no Senado, o sistema declara “amostra pequena” e não produz esse sinal para senadores.

A carga integrada preserva também o cadastro oficial de quem não aparece nos documentos do exercício. Assim, Jorge Kajuru é apresentado como cadastrado sem registro CEAPS em 2025, e não com valor zero. Os deputados federais são identificados por `ideCadastro`; os senadores, por `COD_SENADOR`, conciliado com a relação oficial da 57ª Legislatura. O arquivo CEAPS usado nesta versão vem do endpoint administrativo oficial `/adm-dadosabertos/api/v1/senadores/despesas_ceaps/2025/csv`.

A interface declara a cobertura por esfera: CEAP, CEAPS e verba indenizatória da Alego disponíveis; vereadores pendentes por inexistência de uma base centralizada para as 246 câmaras municipais. Essa distinção impede que falta de dados seja interpretada como inexistência de gastos.

## 19. Incremento 20 — integração da verba indenizatória da Alego

O Portal da Transparência da Alego oferece dados abertos em JSON. A integração consulta primeiro `/api/transparencia/verbas_indenizatorias/periodos` e, para cada mês do exercício, usa `/api/transparencia/verbas_indenizatorias.json?ano=AAAA&mes=M&todos=true`. O retorno fornece identificadores estáveis da prestação e do parlamentar, nome, valor apresentado e valor efetivamente indenizado.

Uma tentativa inicial de obter todas as notas por deputado/mês exigiria aproximadamente quinhentas requisições anuais e produziu timeout no servidor oficial. O lote em preparação foi rejeitado automaticamente, mantendo a versão anterior ativa. A solução definitiva passou a usar os doze resumos mensais consolidados. Isso reduziu a carga para doze consultas, completadas em cerca de onze segundos, sem sacrificar as métricas comparativas de total, média e pico.

Em 2025, foram carregadas 492 prestações mensais pertencentes a 44 deputados estaduais que apareceram em pelo menos um mês. Esse total de pessoas não representa cadeiras simultâneas: pode incluir titulares, suplentes e substituições durante o ano. Os valores indenizados estaduais somaram R$ 19.306.029,46; somadas as três fontes parlamentares integradas, o lote alcançou R$ 27.255.136,10.

A interface denomina esses registros de “prestações mensais”, nunca de documentos fiscais. Como o resumo não discrimina categoria nem fornecedor, o sistema não inventa essas dimensões; apresenta total, diferença entre valor apresentado e indenizado, média mensal, pico e comparação com a mediana da coorte estadual, mantendo link para o detalhamento oficial.
