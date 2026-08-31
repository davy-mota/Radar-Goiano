ALTER TABLE fatos_empenhos ADD COLUMN IF NOT EXISTS ano_exercicio integer;
ALTER TABLE fatos_liquidacoes ADD COLUMN IF NOT EXISTS ano_exercicio integer;
ALTER TABLE fatos_pagamentos ADD COLUMN IF NOT EXISTS ano_exercicio integer;

CREATE INDEX IF NOT EXISTS idx_empenhos_versao_exercicio ON fatos_empenhos (versao_id, ano_exercicio);
CREATE INDEX IF NOT EXISTS idx_liquidacoes_versao_exercicio ON fatos_liquidacoes (versao_id, ano_exercicio);
CREATE INDEX IF NOT EXISTS idx_pagamentos_v2_versao_exercicio ON fatos_pagamentos (versao_id, ano_exercicio);

COMMENT ON COLUMN fatos_empenhos.ano IS 'Ano do movimento segundo a data do empenho.';
COMMENT ON COLUMN fatos_empenhos.ano_exercicio IS 'Exercício orçamentário informado pela fonte.';
COMMENT ON COLUMN fatos_liquidacoes.ano IS 'Ano do movimento segundo a data da liquidação.';
COMMENT ON COLUMN fatos_liquidacoes.ano_exercicio IS 'Exercício do empenho informado pela fonte.';
COMMENT ON COLUMN fatos_pagamentos.ano IS 'Ano do movimento de pagamento informado pela fonte/data.';
COMMENT ON COLUMN fatos_pagamentos.ano_exercicio IS 'Exercício do empenho relacionado ao pagamento.';

-- SELECT f.* em uma view é expandido para a lista de colunas existente no momento da
-- criação (008_camadas_financeiras_versionadas.sql), então as views precisam ser
-- recriadas para incluir ano_exercicio, adicionada acima.
CREATE OR REPLACE VIEW vw_empenhos_ativos AS SELECT f.* FROM fatos_empenhos f JOIN versoes_dados v ON v.id=f.versao_id WHERE v.status='ativa';
CREATE OR REPLACE VIEW vw_liquidacoes_ativas AS SELECT f.* FROM fatos_liquidacoes f JOIN versoes_dados v ON v.id=f.versao_id WHERE v.status='ativa';
CREATE OR REPLACE VIEW vw_pagamentos_ativos AS SELECT f.* FROM fatos_pagamentos f JOIN versoes_dados v ON v.id=f.versao_id WHERE v.status='ativa';
