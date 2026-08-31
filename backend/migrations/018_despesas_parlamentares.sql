-- Cota parlamentar de deputados federais (CEAP) e de senadores (CEAPS) por Goiás.
-- Segue o mesmo modelo de lote/fato usado em emendas e repasses (016/014), com uma
-- diferença deliberada: lá, o índice único de lote ativo é por tabela inteira
-- (uq_lote_emendas_ativo em ((status))), o que só funciona porque cada uma carregou
-- um único exercício até agora. Aqui a tela mostra a série histórica (múltiplos
-- exercícios simultâneos, como no Perfil do Governador), então o índice de lote
-- ativo é por (status, ano): cada exercício tem seu próprio lote ativo, e recarregar
-- um ano arquiva apenas o lote anterior daquele mesmo ano.

CREATE TABLE IF NOT EXISTS lotes_deputados (
    id BIGSERIAL PRIMARY KEY,
    status TEXT NOT NULL CHECK (status IN ('preparando','ativo','arquivado','rejeitado')),
    ano INTEGER NOT NULL,
    recurso JSONB NOT NULL DEFAULT '{}'::jsonb,
    metricas JSONB NOT NULL DEFAULT '{}'::jsonb,
    observacao TEXT,
    criado_em TIMESTAMPTZ NOT NULL DEFAULT now(),
    finalizado_em TIMESTAMPTZ
);

CREATE UNIQUE INDEX IF NOT EXISTS uq_lote_deputados_ativo_por_ano
    ON lotes_deputados ((status), ano) WHERE status = 'ativo';

CREATE TABLE IF NOT EXISTS fatos_despesas_deputados (
    id BIGSERIAL PRIMARY KEY,
    lote_id BIGINT NOT NULL REFERENCES lotes_deputados(id),
    ano INTEGER NOT NULL,
    mes INTEGER,
    deputado_id INTEGER NOT NULL,
    nome_deputado TEXT NOT NULL,
    partido TEXT,
    categoria_despesa TEXT,
    fornecedor TEXT,
    cnpj_cpf_fornecedor TEXT,
    data_documento DATE,
    valor_documento NUMERIC(18,2) NOT NULL DEFAULT 0,
    valor_glosa NUMERIC(18,2) NOT NULL DEFAULT 0,
    valor_liquido NUMERIC(18,2) NOT NULL DEFAULT 0,
    documento_id TEXT,
    url_documento TEXT,
    chave_conteudo CHAR(64) NOT NULL,
    UNIQUE (lote_id, chave_conteudo)
);

CREATE INDEX IF NOT EXISTS idx_despesas_deputados_lote_ano ON fatos_despesas_deputados (lote_id, ano);
CREATE INDEX IF NOT EXISTS idx_despesas_deputados_deputado ON fatos_despesas_deputados (lote_id, deputado_id);

CREATE OR REPLACE VIEW vw_despesas_deputados_ativas AS
SELECT f.*
FROM fatos_despesas_deputados f
JOIN lotes_deputados l ON l.id = f.lote_id AND l.status = 'ativo';

CREATE TABLE IF NOT EXISTS lotes_senadores (
    id BIGSERIAL PRIMARY KEY,
    status TEXT NOT NULL CHECK (status IN ('preparando','ativo','arquivado','rejeitado')),
    ano INTEGER NOT NULL,
    recurso JSONB NOT NULL DEFAULT '{}'::jsonb,
    metricas JSONB NOT NULL DEFAULT '{}'::jsonb,
    observacao TEXT,
    criado_em TIMESTAMPTZ NOT NULL DEFAULT now(),
    finalizado_em TIMESTAMPTZ
);

CREATE UNIQUE INDEX IF NOT EXISTS uq_lote_senadores_ativo_por_ano
    ON lotes_senadores ((status), ano) WHERE status = 'ativo';

CREATE TABLE IF NOT EXISTS fatos_despesas_senadores (
    id BIGSERIAL PRIMARY KEY,
    lote_id BIGINT NOT NULL REFERENCES lotes_senadores(id),
    ano INTEGER NOT NULL,
    mes INTEGER,
    nome_senador TEXT NOT NULL,
    partido TEXT,
    papel TEXT,
    tipo_despesa TEXT,
    cnpj_cpf TEXT,
    fornecedor TEXT,
    documento TEXT,
    data_documento DATE,
    detalhamento TEXT,
    valor_reembolsado NUMERIC(18,2) NOT NULL DEFAULT 0,
    cod_documento TEXT,
    chave_conteudo CHAR(64) NOT NULL,
    UNIQUE (lote_id, chave_conteudo)
);

CREATE INDEX IF NOT EXISTS idx_despesas_senadores_lote_ano ON fatos_despesas_senadores (lote_id, ano);
CREATE INDEX IF NOT EXISTS idx_despesas_senadores_nome ON fatos_despesas_senadores (lote_id, nome_senador);

CREATE OR REPLACE VIEW vw_despesas_senadores_ativas AS
SELECT f.*
FROM fatos_despesas_senadores f
JOIN lotes_senadores l ON l.id = f.lote_id AND l.status = 'ativo';
