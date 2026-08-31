CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_pagamentos_assinatura_duplicidade
ON pagamentos_estaduais (
    ano_exercicio, numero_empenho, data_emissao, valor_pago
);

CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_pagamentos_ano_mes_pago
ON pagamentos_estaduais (ano_exercicio, mes_exercicio, valor_pago);
