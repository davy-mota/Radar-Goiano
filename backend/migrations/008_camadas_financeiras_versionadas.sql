CREATE TABLE IF NOT EXISTS versoes_dados (
    id BIGSERIAL PRIMARY KEY,
    status varchar(12) NOT NULL CHECK (status IN ('preparando', 'validada', 'ativa', 'rejeitada', 'arquivada')),
    iniciado_em timestamptz NOT NULL DEFAULT now(),
    finalizado_em timestamptz,
    catalogo_consultado_em timestamptz NOT NULL DEFAULT now(),
    observacao text,
    metricas jsonb NOT NULL DEFAULT '{}'::jsonb
);

CREATE UNIQUE INDEX IF NOT EXISTS idx_uma_versao_ativa
    ON versoes_dados ((status)) WHERE status = 'ativa';

CREATE TABLE IF NOT EXISTS recursos_ingestao (
    id BIGSERIAL PRIMARY KEY,
    versao_id bigint NOT NULL REFERENCES versoes_dados(id) ON DELETE CASCADE,
    conjunto varchar(20) NOT NULL CHECK (conjunto IN ('empenhos', 'liquidacoes', 'pagamentos', 'receitas')),
    recurso_ckan_id uuid NOT NULL,
    nome text NOT NULL,
    url text NOT NULL,
    formato varchar(5) NOT NULL CHECK (formato IN ('CSV', 'ZIP')),
    modificado_em timestamptz,
    sha256 char(64) NOT NULL,
    bytes_baixados bigint NOT NULL CHECK (bytes_baixados >= 0),
    registros bigint NOT NULL CHECK (registros >= 0),
    importado_em timestamptz NOT NULL DEFAULT now(),
    UNIQUE (versao_id, conjunto, recurso_ckan_id)
);

CREATE TABLE IF NOT EXISTS fatos_empenhos (
    id bigserial PRIMARY KEY, versao_id bigint NOT NULL REFERENCES versoes_dados(id) ON DELETE CASCADE,
    recurso_id bigint NOT NULL REFERENCES recursos_ingestao(id) ON DELETE CASCADE, linha_origem bigint NOT NULL,
    ano integer NOT NULL, mes smallint NOT NULL, numero_empenho text, numero_processo text,
    codigo_orgao text, nome_orgao text, documento_credor text, nome_credor text,
    data_empenho date, dotacao text, descricao text, valor_empenhado numeric(20,2) NOT NULL,
    chave_conteudo char(64) NOT NULL, UNIQUE (recurso_id, linha_origem)
);

CREATE TABLE IF NOT EXISTS fatos_liquidacoes (
    id bigserial PRIMARY KEY, versao_id bigint NOT NULL REFERENCES versoes_dados(id) ON DELETE CASCADE,
    recurso_id bigint NOT NULL REFERENCES recursos_ingestao(id) ON DELETE CASCADE, linha_origem bigint NOT NULL,
    ano integer NOT NULL, mes smallint NOT NULL, codigo_liquidacao text, numero_empenho text,
    codigo_orgao text, nome_orgao text, documento_credor text, nome_credor text,
    data_liquidacao date, descricao text, valor_liquidado numeric(20,2) NOT NULL,
    chave_conteudo char(64) NOT NULL, UNIQUE (recurso_id, linha_origem)
);

CREATE TABLE IF NOT EXISTS fatos_pagamentos (
    id bigserial PRIMARY KEY, versao_id bigint NOT NULL REFERENCES versoes_dados(id) ON DELETE CASCADE,
    recurso_id bigint NOT NULL REFERENCES recursos_ingestao(id) ON DELETE CASCADE, linha_origem bigint NOT NULL,
    ano integer NOT NULL, mes smallint NOT NULL, numero_sequencial_op text, numero_empenho text,
    codigo_orgao text, nome_orgao text, documento_credor text, nome_credor text,
    data_pagamento date, dotacao text, descricao text, valor_pago numeric(20,2) NOT NULL,
    chave_conteudo char(64) NOT NULL, UNIQUE (recurso_id, linha_origem)
);

CREATE TABLE IF NOT EXISTS fatos_receitas (
    id bigserial PRIMARY KEY, versao_id bigint NOT NULL REFERENCES versoes_dados(id) ON DELETE CASCADE,
    recurso_id bigint NOT NULL REFERENCES recursos_ingestao(id) ON DELETE CASCADE, linha_origem bigint NOT NULL,
    ano integer NOT NULL, mes smallint NOT NULL, codigo_orgao text, nome_orgao text,
    categoria_economica text, origem text, especie text, rubrica text, alinea text, subalinea text,
    codigo_natureza text, valor_previsto numeric(20,2) NOT NULL, valor_realizado numeric(20,2) NOT NULL,
    chave_conteudo char(64) NOT NULL, UNIQUE (recurso_id, linha_origem)
);

CREATE INDEX IF NOT EXISTS idx_empenhos_versao_ano_mes ON fatos_empenhos (versao_id, ano, mes);
CREATE INDEX IF NOT EXISTS idx_liquidacoes_versao_ano_mes ON fatos_liquidacoes (versao_id, ano, mes);
CREATE INDEX IF NOT EXISTS idx_pagamentos_v2_versao_ano_mes ON fatos_pagamentos (versao_id, ano, mes);
CREATE INDEX IF NOT EXISTS idx_receitas_v2_versao_ano_mes ON fatos_receitas (versao_id, ano, mes);
CREATE INDEX IF NOT EXISTS idx_empenhos_chave ON fatos_empenhos (versao_id, chave_conteudo);
CREATE INDEX IF NOT EXISTS idx_liquidacoes_chave ON fatos_liquidacoes (versao_id, chave_conteudo);
CREATE INDEX IF NOT EXISTS idx_pagamentos_v2_chave ON fatos_pagamentos (versao_id, chave_conteudo);
CREATE INDEX IF NOT EXISTS idx_receitas_v2_chave ON fatos_receitas (versao_id, chave_conteudo);

CREATE OR REPLACE VIEW vw_empenhos_ativos AS SELECT f.* FROM fatos_empenhos f JOIN versoes_dados v ON v.id=f.versao_id WHERE v.status='ativa';
CREATE OR REPLACE VIEW vw_liquidacoes_ativas AS SELECT f.* FROM fatos_liquidacoes f JOIN versoes_dados v ON v.id=f.versao_id WHERE v.status='ativa';
CREATE OR REPLACE VIEW vw_pagamentos_ativos AS SELECT f.* FROM fatos_pagamentos f JOIN versoes_dados v ON v.id=f.versao_id WHERE v.status='ativa';
CREATE OR REPLACE VIEW vw_receitas_ativas AS SELECT f.* FROM fatos_receitas f JOIN versoes_dados v ON v.id=f.versao_id WHERE v.status='ativa';
