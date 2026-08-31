CREATE TABLE IF NOT EXISTS lotes_execucao_orcamentaria (
    id BIGSERIAL PRIMARY KEY,
    status TEXT NOT NULL CHECK (status IN ('preparando','validado','ativo','arquivado','rejeitado')),
    criado_em TIMESTAMPTZ NOT NULL DEFAULT now(),
    finalizado_em TIMESTAMPTZ,
    recursos JSONB NOT NULL DEFAULT '[]',
    metricas JSONB NOT NULL DEFAULT '{}',
    observacao TEXT
);

CREATE UNIQUE INDEX IF NOT EXISTS idx_um_lote_execucao_ativo
    ON lotes_execucao_orcamentaria ((status)) WHERE status = 'ativo';

CREATE TABLE IF NOT EXISTS fatos_execucao_orcamentaria (
    id BIGSERIAL PRIMARY KEY,
    lote_id BIGINT NOT NULL REFERENCES lotes_execucao_orcamentaria(id) ON DELETE CASCADE,
    recurso_id TEXT NOT NULL,
    ano_exercicio INTEGER NOT NULL,
    mes INTEGER NOT NULL CHECK (mes BETWEEN 1 AND 12),
    codigo_orgao TEXT, nome_orgao TEXT,
    codigo_funcao TEXT, nome_funcao TEXT,
    codigo_subfuncao TEXT, nome_subfuncao TEXT,
    codigo_programa TEXT, nome_programa TEXT,
    codigo_acao TEXT, nome_acao TEXT,
    codigo_categoria TEXT, nome_categoria TEXT,
    codigo_grupo TEXT, nome_grupo TEXT,
    codigo_modalidade TEXT, nome_modalidade TEXT,
    codigo_elemento TEXT, nome_elemento TEXT,
    valor_empenhado NUMERIC(18,2) NOT NULL DEFAULT 0,
    valor_liquidado NUMERIC(18,2) NOT NULL DEFAULT 0,
    valor_pago NUMERIC(18,2) NOT NULL DEFAULT 0,
    chave_conteudo TEXT NOT NULL,
    UNIQUE (lote_id, chave_conteudo)
);

CREATE INDEX IF NOT EXISTS idx_execucao_classificada_ano_funcao
    ON fatos_execucao_orcamentaria (lote_id, ano_exercicio, nome_funcao);
CREATE INDEX IF NOT EXISTS idx_execucao_classificada_ano_grupo
    ON fatos_execucao_orcamentaria (lote_id, ano_exercicio, nome_grupo);

CREATE OR REPLACE VIEW vw_execucao_orcamentaria_ativa AS
SELECT f.* FROM fatos_execucao_orcamentaria f
JOIN lotes_execucao_orcamentaria l ON l.id=f.lote_id AND l.status='ativo';
