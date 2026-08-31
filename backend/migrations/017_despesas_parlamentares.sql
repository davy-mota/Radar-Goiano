CREATE TABLE IF NOT EXISTS lotes_despesas_parlamentares (
    id BIGSERIAL PRIMARY KEY,
    ano INTEGER NOT NULL,
    status TEXT NOT NULL CHECK (status IN ('preparando','ativo','arquivado','rejeitado')),
    recursos JSONB NOT NULL DEFAULT '[]'::jsonb,
    metricas JSONB NOT NULL DEFAULT '{}'::jsonb,
    observacao TEXT,
    criado_em TIMESTAMPTZ NOT NULL DEFAULT now(),
    finalizado_em TIMESTAMPTZ
);

CREATE UNIQUE INDEX IF NOT EXISTS uq_despesas_parlamentares_ano_ativo
    ON lotes_despesas_parlamentares (ano) WHERE status='ativo';

CREATE TABLE IF NOT EXISTS fatos_despesas_parlamentares (
    id BIGSERIAL PRIMARY KEY,
    lote_id BIGINT NOT NULL REFERENCES lotes_despesas_parlamentares(id),
    ano INTEGER NOT NULL,
    mes INTEGER NOT NULL CHECK (mes BETWEEN 1 AND 12),
    data_documento DATE,
    cargo TEXT NOT NULL CHECK (cargo IN ('deputado_federal','senador')),
    fonte TEXT NOT NULL,
    parlamentar_codigo TEXT NOT NULL,
    parlamentar_nome TEXT NOT NULL,
    partido TEXT,
    categoria TEXT NOT NULL,
    fornecedor_nome TEXT,
    fornecedor_documento TEXT,
    documento_numero TEXT,
    valor_documento NUMERIC(18,2) NOT NULL DEFAULT 0,
    valor_glosa NUMERIC(18,2) NOT NULL DEFAULT 0,
    valor_reembolsado NUMERIC(18,2) NOT NULL DEFAULT 0,
    documento_url TEXT,
    chave_conteudo CHAR(64) NOT NULL,
    UNIQUE (lote_id,chave_conteudo)
);

CREATE TABLE IF NOT EXISTS parlamentares_lote (
    lote_id BIGINT NOT NULL REFERENCES lotes_despesas_parlamentares(id),
    cargo TEXT NOT NULL CHECK (cargo IN ('deputado_federal','senador')),
    parlamentar_codigo TEXT NOT NULL,
    parlamentar_nome TEXT NOT NULL,
    partido TEXT,
    uf CHAR(2) NOT NULL DEFAULT 'GO',
    PRIMARY KEY (lote_id,cargo,parlamentar_codigo)
);

CREATE INDEX IF NOT EXISTS idx_desp_parlamentar_consulta
    ON fatos_despesas_parlamentares (lote_id,cargo,parlamentar_codigo,mes);

CREATE OR REPLACE VIEW vw_despesas_parlamentares_ativas AS
SELECT f.* FROM fatos_despesas_parlamentares f
JOIN lotes_despesas_parlamentares l ON l.id=f.lote_id AND l.status='ativo';
