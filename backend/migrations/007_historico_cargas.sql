CREATE TABLE IF NOT EXISTS historico_cargas (
    id BIGSERIAL PRIMARY KEY,
    conjunto VARCHAR(30) NOT NULL,
    status VARCHAR(15) NOT NULL CHECK (status IN ('em_execucao', 'sucesso', 'falha')),
    fonte TEXT NOT NULL,
    iniciado_em TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    finalizado_em TIMESTAMPTZ,
    registros_processados BIGINT,
    duracao_segundos NUMERIC(14, 3),
    mensagem_erro TEXT,
    CONSTRAINT historico_cargas_finalizacao_coerente CHECK (
        (status = 'em_execucao' AND finalizado_em IS NULL)
        OR (status IN ('sucesso', 'falha') AND finalizado_em IS NOT NULL)
    )
);

CREATE INDEX IF NOT EXISTS idx_historico_cargas_conjunto_inicio
    ON historico_cargas (conjunto, iniciado_em DESC);

CREATE INDEX IF NOT EXISTS idx_historico_cargas_status_inicio
    ON historico_cargas (status, iniciado_em DESC);
