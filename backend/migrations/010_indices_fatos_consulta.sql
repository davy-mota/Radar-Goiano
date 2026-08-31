CREATE INDEX IF NOT EXISTS idx_pagamentos_v2_exercicio_orgao
    ON fatos_pagamentos (ano_exercicio, normalizar_texto_utf8(nome_orgao));
CREATE INDEX IF NOT EXISTS idx_pagamentos_v2_documento_normalizado
    ON fatos_pagamentos ((
        CASE
            WHEN documento_credor ~ '^[0-9.\/-]+$'
             AND length(regexp_replace(documento_credor, '[^0-9]', '', 'g')) BETWEEN 12 AND 14
            THEN lpad(regexp_replace(documento_credor, '[^0-9]', '', 'g'), 14, '0')
        END
    ));

CREATE INDEX IF NOT EXISTS idx_empenhos_exercicio_orgao
    ON fatos_empenhos (ano_exercicio, normalizar_texto_utf8(nome_orgao));
CREATE INDEX IF NOT EXISTS idx_empenhos_documento_normalizado
    ON fatos_empenhos ((
        CASE
            WHEN documento_credor ~ '^[0-9.\/-]+$'
             AND length(regexp_replace(documento_credor, '[^0-9]', '', 'g')) BETWEEN 12 AND 14
            THEN lpad(regexp_replace(documento_credor, '[^0-9]', '', 'g'), 14, '0')
        END
    ));

CREATE INDEX IF NOT EXISTS idx_liquidacoes_exercicio_orgao
    ON fatos_liquidacoes (ano_exercicio, normalizar_texto_utf8(nome_orgao));
CREATE INDEX IF NOT EXISTS idx_liquidacoes_documento_normalizado
    ON fatos_liquidacoes ((
        CASE
            WHEN documento_credor ~ '^[0-9.\/-]+$'
             AND length(regexp_replace(documento_credor, '[^0-9]', '', 'g')) BETWEEN 12 AND 14
            THEN lpad(regexp_replace(documento_credor, '[^0-9]', '', 'g'), 14, '0')
        END
    ));

DROP INDEX IF EXISTS idx_pagamentos_v2_documento_credor;
DROP INDEX IF EXISTS idx_empenhos_documento_credor;
DROP INDEX IF EXISTS idx_liquidacoes_documento_credor;
