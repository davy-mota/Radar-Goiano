-- Auditoria somente leitura. Não altera nenhuma tabela.
\pset pager off
\timing on

SELECT 'pagamentos' AS conjunto, COUNT(*) AS registros, MIN(ano_exercicio) AS ano_min,
       MAX(ano_exercicio) AS ano_max, COUNT(DISTINCT ano_exercicio) AS anos
FROM pagamentos_estaduais
UNION ALL
SELECT 'receitas', COUNT(*), MIN(ano_exercicio), MAX(ano_exercicio), COUNT(DISTINCT ano_exercicio)
FROM receitas_estaduais
UNION ALL
SELECT 'contratos', COUNT(*), MIN(ano_exercicio), MAX(ano_exercicio), COUNT(DISTINCT ano_exercicio)
FROM contratos_licitacoes
UNION ALL
SELECT 'folha', COUNT(*), MIN(ano_exercicio), MAX(ano_exercicio), COUNT(DISTINCT ano_exercicio)
FROM folha_pagamento
UNION ALL
SELECT 'diarias', COUNT(*), MIN(ano_exercicio), MAX(ano_exercicio), COUNT(DISTINCT ano_exercicio)
FROM diarias_passagens;

SELECT ano_exercicio, COUNT(*) AS registros, ROUND(SUM(valor_pago)::numeric, 2) AS total_pago,
       COUNT(*) FILTER (WHERE valor_pago < 0) AS valores_negativos,
       COUNT(*) FILTER (WHERE numero_empenho IS NULL OR btrim(numero_empenho) = '') AS sem_empenho,
       COUNT(*) FILTER (WHERE nome_orgao IS NULL OR btrim(nome_orgao) = '') AS sem_orgao,
       COUNT(*) FILTER (WHERE nome_credor IS NULL OR btrim(nome_credor) = '') AS sem_credor,
       COUNT(*) FILTER (WHERE data_emissao IS NULL) AS sem_data
FROM pagamentos_estaduais
GROUP BY ano_exercicio
ORDER BY ano_exercicio;

SELECT
    COUNT(*) FILTER (WHERE ano_exercicio NOT BETWEEN 2003 AND EXTRACT(YEAR FROM CURRENT_DATE)::int) AS ano_invalido,
    COUNT(*) FILTER (WHERE mes_exercicio NOT BETWEEN 1 AND 12) AS mes_invalido,
    COUNT(*) FILTER (WHERE data_emissao IS NOT NULL AND EXTRACT(YEAR FROM data_emissao)::int <> ano_exercicio) AS data_ano_divergente,
    COUNT(*) FILTER (WHERE valor_pago > 1000000000) AS pagamentos_acima_1_bilhao,
    COUNT(*) FILTER (WHERE length(regexp_replace(COALESCE(cnpj_cpf_credor, ''), '\D', '', 'g')) NOT IN (0, 11, 14)) AS documento_tamanho_atipico
FROM pagamentos_estaduais;

SELECT COUNT(*) AS grupos_duplicados, COALESCE(SUM(quantidade - 1), 0) AS linhas_excedentes
FROM (
    SELECT COUNT(*) AS quantidade
    FROM pagamentos_estaduais
    GROUP BY ano_exercicio, mes_exercicio, numero_empenho, cnpj_cpf_credor,
             nome_credor, data_emissao, valor_pago
    HAVING COUNT(*) > 1
) duplicados;

SELECT ano_exercicio, COUNT(*) AS registros,
       ROUND(SUM(valor_arrecadado)::numeric, 2) AS total_arrecadado,
       COUNT(*) FILTER (WHERE valor_arrecadado < 0) AS valores_negativos,
       COUNT(*) FILTER (WHERE nome_orgao IS NULL OR btrim(nome_orgao) = '') AS sem_orgao,
       COUNT(*) FILTER (WHERE data_arrecadacao IS NULL) AS sem_data
FROM receitas_estaduais
GROUP BY ano_exercicio
ORDER BY ano_exercicio;

SELECT 'contratos' AS conjunto,
       COUNT(*) FILTER (WHERE valor_contrato < 0) AS valores_negativos,
       COUNT(*) FILTER (WHERE nome_orgao IS NULL OR btrim(nome_orgao) = '') AS sem_orgao,
       COUNT(*) FILTER (WHERE numero_contrato IS NULL OR btrim(numero_contrato) = '') AS sem_identificador,
       COUNT(*) FILTER (WHERE data_assinatura IS NULL) AS sem_data
FROM contratos_licitacoes
UNION ALL
SELECT 'folha',
       COUNT(*) FILTER (WHERE valor_remuneracao_bruta < 0),
       COUNT(*) FILTER (WHERE nome_orgao IS NULL OR btrim(nome_orgao) = ''),
       COUNT(*) FILTER (WHERE nome_servidor IS NULL OR btrim(nome_servidor) = ''),
       COUNT(*) FILTER (WHERE mes_exercicio NOT BETWEEN 1 AND 12)
FROM folha_pagamento
UNION ALL
SELECT 'diarias',
       COUNT(*) FILTER (WHERE valor_total < 0),
       COUNT(*) FILTER (WHERE nome_orgao IS NULL OR btrim(nome_orgao) = ''),
       COUNT(*) FILTER (WHERE nome_servidor IS NULL OR btrim(nome_servidor) = ''),
       COUNT(*) FILTER (WHERE destino IS NULL OR btrim(destino) = '')
FROM diarias_passagens;
