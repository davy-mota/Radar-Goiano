CREATE TABLE IF NOT EXISTS municipios_ibge (
    codigo_ibge INTEGER PRIMARY KEY,
    nome TEXT NOT NULL,
    uf CHAR(2) NOT NULL DEFAULT 'GO',
    regiao_imediata TEXT,
    regiao_intermediaria TEXT,
    atualizado_em TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE TABLE IF NOT EXISTS populacoes_municipais (
    codigo_ibge INTEGER NOT NULL REFERENCES municipios_ibge(codigo_ibge),
    ano INTEGER NOT NULL CHECK (ano BETWEEN 1900 AND 2100),
    populacao BIGINT NOT NULL CHECK (populacao > 0),
    referencia DATE NOT NULL,
    fonte_url TEXT NOT NULL,
    carregado_em TIMESTAMPTZ NOT NULL DEFAULT now(),
    PRIMARY KEY (codigo_ibge, ano)
);

CREATE TABLE IF NOT EXISTS aliases_municipios (
    fonte TEXT NOT NULL,
    nome_origem TEXT NOT NULL,
    nome_normalizado TEXT NOT NULL,
    codigo_ibge INTEGER REFERENCES municipios_ibge(codigo_ibge),
    metodo TEXT NOT NULL CHECK (metodo IN ('exato_normalizado', 'manual', 'pendente')),
    revisado_em TIMESTAMPTZ,
    observacao TEXT,
    PRIMARY KEY (fonte, nome_origem)
);

CREATE INDEX IF NOT EXISTS idx_aliases_municipios_codigo
    ON aliases_municipios (codigo_ibge);

CREATE OR REPLACE VIEW vw_repasses_municipais_canonicos AS
SELECT
    r.*,
    a.codigo_ibge,
    m.nome AS municipio_canonico,
    p.populacao,
    CASE WHEN p.populacao > 0
        THEN (r.credito_icms + r.credito_ipi + r.credito_ipva) / p.populacao
    END AS valor_per_capita
FROM vw_repasses_municipais_ativos r
LEFT JOIN aliases_municipios a
    ON a.fonte = 'repasses_goias' AND a.nome_origem = r.municipio
LEFT JOIN municipios_ibge m ON m.codigo_ibge = a.codigo_ibge
LEFT JOIN populacoes_municipais p
    ON p.codigo_ibge = a.codigo_ibge AND p.ano = r.ano;
