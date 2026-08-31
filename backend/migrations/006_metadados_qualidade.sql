CREATE TABLE IF NOT EXISTS metadados_qualidade (
    conjunto varchar(40) PRIMARY KEY,
    registros bigint NOT NULL,
    ano_min integer,
    ano_max integer,
    maior_data_referencia date,
    qualidade jsonb NOT NULL,
    calculado_em timestamptz NOT NULL DEFAULT now()
);

CREATE OR REPLACE FUNCTION atualizar_metadados_qualidade()
RETURNS void LANGUAGE plpgsql AS $$
BEGIN
    INSERT INTO metadados_qualidade
    SELECT 'pagamentos', COUNT(*), MIN(ano_exercicio), MAX(ano_exercicio), MAX(data_emissao),
           jsonb_build_object(
               'empenho_preenchido_pct', COALESCE(100.0 * COUNT(*) FILTER (WHERE numero_empenho IS NOT NULL AND btrim(numero_empenho) <> '') / NULLIF(COUNT(*), 0), 0),
               'orgao_preenchido_pct', COALESCE(100.0 * COUNT(*) FILTER (WHERE nome_orgao IS NOT NULL AND btrim(nome_orgao) <> '') / NULLIF(COUNT(*), 0), 0),
               'credor_preenchido_pct', COALESCE(100.0 * COUNT(*) FILTER (WHERE nome_credor IS NOT NULL AND btrim(nome_credor) <> '') / NULLIF(COUNT(*), 0), 0)
           ), now() FROM pagamentos_estaduais
    ON CONFLICT (conjunto) DO UPDATE SET registros=EXCLUDED.registros, ano_min=EXCLUDED.ano_min, ano_max=EXCLUDED.ano_max, maior_data_referencia=EXCLUDED.maior_data_referencia, qualidade=EXCLUDED.qualidade, calculado_em=EXCLUDED.calculado_em;

    INSERT INTO metadados_qualidade
    SELECT 'receitas', COUNT(*), MIN(ano_exercicio), MAX(ano_exercicio), NULL::date,
           jsonb_build_object(
               'previsao_positiva_pct', COALESCE(100.0 * COUNT(*) FILTER (WHERE valor_previsto > 0) / NULLIF(COUNT(*), 0), 0),
               'arrecadacao_preenchida_pct', COALESCE(100.0 * COUNT(*) FILTER (WHERE valor_arrecadado IS NOT NULL) / NULLIF(COUNT(*), 0), 0),
               'data_preenchida_pct', COALESCE(100.0 * COUNT(*) FILTER (WHERE data_arrecadacao IS NOT NULL) / NULLIF(COUNT(*), 0), 0)
           ), now() FROM receitas_estaduais
    ON CONFLICT (conjunto) DO UPDATE SET registros=EXCLUDED.registros, ano_min=EXCLUDED.ano_min, ano_max=EXCLUDED.ano_max, maior_data_referencia=EXCLUDED.maior_data_referencia, qualidade=EXCLUDED.qualidade, calculado_em=EXCLUDED.calculado_em;

    INSERT INTO metadados_qualidade
    SELECT 'contratos', COUNT(*), MIN(ano_exercicio), MAX(ano_exercicio), MAX(data_assinatura),
           jsonb_build_object(
               'documento_preenchido_pct', COALESCE(100.0 * COUNT(*) FILTER (WHERE cnpj_cpf_contratado IS NOT NULL AND btrim(cnpj_cpf_contratado) <> '') / NULLIF(COUNT(*), 0), 0),
               'objeto_preenchido_pct', COALESCE(100.0 * COUNT(*) FILTER (WHERE objeto_contrato IS NOT NULL AND btrim(objeto_contrato) <> '') / NULLIF(COUNT(*), 0), 0)
           ), now() FROM contratos_licitacoes
    ON CONFLICT (conjunto) DO UPDATE SET registros=EXCLUDED.registros, ano_min=EXCLUDED.ano_min, ano_max=EXCLUDED.ano_max, maior_data_referencia=EXCLUDED.maior_data_referencia, qualidade=EXCLUDED.qualidade, calculado_em=EXCLUDED.calculado_em;

    INSERT INTO metadados_qualidade
    SELECT 'folha', COUNT(*), MIN(ano_exercicio), MAX(ano_exercicio), NULL::date,
           jsonb_build_object(
               'orgao_preenchido_pct', COALESCE(100.0 * COUNT(*) FILTER (WHERE nome_orgao IS NOT NULL AND btrim(nome_orgao) <> '') / NULLIF(COUNT(*), 0), 0),
               'cargo_preenchido_pct', COALESCE(100.0 * COUNT(*) FILTER (WHERE cargo IS NOT NULL AND btrim(cargo) <> '') / NULLIF(COUNT(*), 0), 0)
           ), now() FROM folha_pagamento
    ON CONFLICT (conjunto) DO UPDATE SET registros=EXCLUDED.registros, ano_min=EXCLUDED.ano_min, ano_max=EXCLUDED.ano_max, maior_data_referencia=EXCLUDED.maior_data_referencia, qualidade=EXCLUDED.qualidade, calculado_em=EXCLUDED.calculado_em;

    INSERT INTO metadados_qualidade
    SELECT 'diarias', COUNT(*), MIN(ano_exercicio), MAX(ano_exercicio), NULL::date,
           jsonb_build_object(
               'destino_preenchido_pct', COALESCE(100.0 * COUNT(*) FILTER (WHERE destino IS NOT NULL AND btrim(destino) <> '') / NULLIF(COUNT(*), 0), 0),
               'motivo_preenchido_pct', COALESCE(100.0 * COUNT(*) FILTER (WHERE motivo_viagem IS NOT NULL AND btrim(motivo_viagem) <> '') / NULLIF(COUNT(*), 0), 0)
           ), now() FROM diarias_passagens
    ON CONFLICT (conjunto) DO UPDATE SET registros=EXCLUDED.registros, ano_min=EXCLUDED.ano_min, ano_max=EXCLUDED.ano_max, maior_data_referencia=EXCLUDED.maior_data_referencia, qualidade=EXCLUDED.qualidade, calculado_em=EXCLUDED.calculado_em;
END;
$$;

SELECT atualizar_metadados_qualidade();
