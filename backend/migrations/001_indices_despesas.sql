-- Executar fora de uma transação para permitir CONCURRENTLY.
CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_pagamentos_ano_mes
    ON pagamentos_estaduais (ano_exercicio, mes_exercicio);

CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_pagamentos_ano_orgao
    ON pagamentos_estaduais (ano_exercicio, nome_orgao);

CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_pagamentos_ano_funcao
    ON pagamentos_estaduais (ano_exercicio, funcao);

CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_pagamentos_ano_valor_pago
    ON pagamentos_estaduais (ano_exercicio, valor_pago DESC);
