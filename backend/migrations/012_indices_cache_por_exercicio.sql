-- Índices de suporte ao gerador incremental de caches.
--
-- IMPORTANTE: executar este arquivo fora de uma transação, pois o uso de
-- CONCURRENTLY mantém as tabelas disponíveis para leitura e escrita durante a
-- construção. IF NOT EXISTS torna a execução repetível.

CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_contratos_cache_ano
    ON contratos_licitacoes (ano_exercicio);

CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_folha_cache_ano
    ON folha_pagamento (ano_exercicio);

CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_diarias_cache_ano
    ON diarias_passagens (ano_exercicio);

ANALYZE contratos_licitacoes (ano_exercicio);
ANALYZE folha_pagamento (ano_exercicio);
ANALYZE diarias_passagens (ano_exercicio);
