-- A conversão depende apenas da entrada. O bloco de exceção preserva textos
-- que eventualmente não possam ser representados em Latin-1.
CREATE OR REPLACE FUNCTION normalizar_texto_utf8(valor text)
RETURNS text
LANGUAGE plpgsql
IMMUTABLE
STRICT
AS $$
BEGIN
    IF valor ~ '[[:cntrl:]]' THEN
        BEGIN
            RETURN btrim(convert_from(convert_to(valor, 'LATIN1'), 'UTF8'));
        EXCEPTION WHEN character_not_in_repertoire THEN
            RETURN btrim(regexp_replace(valor, '[[:cntrl:]]', '', 'g'));
        END;
    END IF;
    RETURN btrim(valor);
END;
$$;

DROP INDEX CONCURRENTLY IF EXISTS idx_pagamentos_ano_orgao_normalizado;

CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_pagamentos_ano_orgao_normalizado
ON pagamentos_estaduais (
    ano_exercicio,
    (normalizar_texto_utf8(nome_orgao))
);
