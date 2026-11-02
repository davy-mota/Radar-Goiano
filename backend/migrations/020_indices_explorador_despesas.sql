-- Índices dedicados ao Explorador de Despesas.
-- CREATE INDEX CONCURRENTLY exige execução fora de uma transação explícita.

CREATE EXTENSION IF NOT EXISTS pg_trgm;

-- Permite obter as maiores despesas sem ordenar todos os pagamentos ativos.
CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_pagamentos_versao_valor_id
    ON fatos_pagamentos (versao_id, valor_pago DESC NULLS LAST, id DESC);

CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_pagamentos_versao_exercicio_valor_id
    ON fatos_pagamentos (versao_id, ano_exercicio, valor_pago DESC NULLS LAST, id DESC);

-- Atende filtro, lista distinta e agregação por órgão em todos os exercícios.
CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_pagamentos_versao_orgao_normalizado
    ON fatos_pagamentos (versao_id, normalizar_texto_utf8(nome_orgao))
    INCLUDE (valor_pago)
    WHERE nome_orgao IS NOT NULL;

-- Busca livre por credor, documento ou número de empenho em uma expressão única.
CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_pagamentos_busca_trigram
    ON fatos_pagamentos USING gin ((
        COALESCE(nome_credor, '') || ' ' ||
        COALESCE(documento_credor, '') || ' ' ||
        COALESCE(numero_empenho, '')
    ) gin_trgm_ops);

-- Agregacao usada pelos KPIs, series mensais e filtros da tela. A quantidade
-- de linhas cai de milhoes de fatos para combinacoes de etapa/ano/mes/orgao.
CREATE MATERIALIZED VIEW IF NOT EXISTS mv_despesas_execucao_mensal AS
SELECT etapa,
       ano_exercicio,
       mes,
       nome_orgao,
       COUNT(*)::bigint AS registros,
       COALESCE(SUM(valor), 0)::numeric AS valor
FROM (
    SELECT 'empenhado'::text AS etapa,
           ano_exercicio,
           mes,
           COALESCE(normalizar_texto_utf8(nome_orgao), '') AS nome_orgao,
           valor_empenhado AS valor
    FROM vw_empenhos_ativos

    UNION ALL

    SELECT 'liquidado'::text AS etapa,
           ano_exercicio,
           mes,
           COALESCE(normalizar_texto_utf8(nome_orgao), '') AS nome_orgao,
           valor_liquidado AS valor
    FROM vw_liquidacoes_ativas

    UNION ALL

    SELECT 'pago'::text AS etapa,
           ano_exercicio,
           mes,
           COALESCE(normalizar_texto_utf8(nome_orgao), '') AS nome_orgao,
           valor_pago AS valor
    FROM vw_pagamentos_ativos
) AS fatos
GROUP BY etapa, ano_exercicio, mes, nome_orgao
WITH DATA;

CREATE UNIQUE INDEX IF NOT EXISTS uq_mv_despesas_execucao_mensal
    ON mv_despesas_execucao_mensal (etapa, ano_exercicio, mes, nome_orgao);

CREATE INDEX IF NOT EXISTS idx_mv_despesas_ano_orgao_etapa
    ON mv_despesas_execucao_mensal (ano_exercicio, nome_orgao, etapa);

ANALYZE fatos_pagamentos;
ANALYZE mv_despesas_execucao_mensal;
