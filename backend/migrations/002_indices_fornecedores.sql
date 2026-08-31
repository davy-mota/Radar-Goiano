-- Índices funcionais para associação por CNPJ normalizado.
-- Executar fora de uma transação para permitir CONCURRENTLY.
CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_pagamentos_cnpj_normalizado
ON pagamentos_estaduais ((
    CASE
        WHEN cnpj_cpf_credor ~ '^[0-9.\/-]+$'
         AND length(regexp_replace(cnpj_cpf_credor, '[^0-9]', '', 'g')) BETWEEN 12 AND 14
        THEN lpad(regexp_replace(cnpj_cpf_credor, '[^0-9]', '', 'g'), 14, '0')
    END
));

CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_contratos_cnpj_normalizado
ON contratos_licitacoes ((
    CASE
        WHEN cnpj_cpf_contratado ~ '^[0-9.\/-]+$'
         AND length(regexp_replace(cnpj_cpf_contratado, '[^0-9]', '', 'g')) BETWEEN 12 AND 14
        THEN lpad(regexp_replace(cnpj_cpf_contratado, '[^0-9]', '', 'g'), 14, '0')
    END
));
