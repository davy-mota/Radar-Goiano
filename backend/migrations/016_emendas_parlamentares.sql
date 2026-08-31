CREATE TABLE IF NOT EXISTS lotes_emendas (
    id BIGSERIAL PRIMARY KEY,
    status TEXT NOT NULL CHECK (status IN ('preparando','ativo','arquivado','rejeitado')),
    ano INTEGER,
    recurso JSONB NOT NULL DEFAULT '{}'::jsonb,
    metricas JSONB NOT NULL DEFAULT '{}'::jsonb,
    observacao TEXT,
    criado_em TIMESTAMPTZ NOT NULL DEFAULT now(),
    finalizado_em TIMESTAMPTZ
);

CREATE UNIQUE INDEX IF NOT EXISTS uq_lote_emendas_ativo
    ON lotes_emendas ((status)) WHERE status = 'ativo';

CREATE TABLE IF NOT EXISTS fatos_emendas (
    id BIGSERIAL PRIMARY KEY,
    lote_id BIGINT NOT NULL REFERENCES lotes_emendas(id),
    ano INTEGER NOT NULL,
    orgao TEXT,
    processo TEXT,
    natureza_codigo TEXT,
    natureza_nome TEXT,
    funcao TEXT,
    subfuncao TEXT,
    empenho_sequencial TEXT,
    descricao TEXT,
    historico TEXT,
    numero_emenda TEXT,
    autor TEXT,
    objeto TEXT,
    municipio_origem TEXT,
    beneficiario TEXT,
    cnpj TEXT,
    numero_pdf TEXT,
    valor_indicado NUMERIC(18,2) NOT NULL DEFAULT 0,
    tipo_emenda TEXT,
    grupo_despesa TEXT,
    data DATE,
    valor_empenhado NUMERIC(18,2) NOT NULL DEFAULT 0,
    valor_liquidado NUMERIC(18,2) NOT NULL DEFAULT 0,
    valor_pago NUMERIC(18,2) NOT NULL DEFAULT 0,
    data_atualizacao DATE,
    chave_conteudo CHAR(64) NOT NULL,
    UNIQUE (lote_id, chave_conteudo)
);

CREATE INDEX IF NOT EXISTS idx_emendas_lote_ano ON fatos_emendas (lote_id, ano);
CREATE INDEX IF NOT EXISTS idx_emendas_autor ON fatos_emendas (lote_id, autor);
CREATE INDEX IF NOT EXISTS idx_emendas_funcao ON fatos_emendas (lote_id, funcao);

CREATE OR REPLACE VIEW vw_emendas_ativas AS
SELECT f.*,a.codigo_ibge,m.nome AS municipio_canonico
FROM fatos_emendas f
JOIN lotes_emendas l ON l.id=f.lote_id AND l.status='ativo'
LEFT JOIN aliases_municipios a
  ON a.fonte='emendas_goias' AND a.nome_origem=f.municipio_origem
LEFT JOIN municipios_ibge m ON m.codigo_ibge=a.codigo_ibge;
