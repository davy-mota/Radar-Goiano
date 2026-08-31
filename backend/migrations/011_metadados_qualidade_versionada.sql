-- Os conjuntos 'pagamentos' e 'receitas' passam a refletir a versão ativa das
-- tabelas fatos_* (Incremento 8), em vez das tabelas legadas pagamentos_estaduais/
-- receitas_estaduais. Contratos, folha e diárias permanecem inalterados: não fazem
-- parte da reconstrução em camadas versionadas.
CREATE OR REPLACE FUNCTION atualizar_metadados_qualidade()
RETURNS void LANGUAGE plpgsql AS $$
BEGIN
    INSERT INTO metadados_qualidade
    SELECT 'pagamentos', COUNT(*), MIN(ano_exercicio), MAX(ano_exercicio), MAX(data_pagamento),
           jsonb_build_object(
               'empenho_preenchido_pct', COALESCE(100.0 * COUNT(*) FILTER (WHERE numero_empenho IS NOT NULL AND btrim(numero_empenho) <> '') / NULLIF(COUNT(*), 0), 0),
               'orgao_preenchido_pct', COALESCE(100.0 * COUNT(*) FILTER (WHERE nome_orgao IS NOT NULL AND btrim(nome_orgao) <> '') / NULLIF(COUNT(*), 0), 0),
               'credor_preenchido_pct', COALESCE(100.0 * COUNT(*) FILTER (WHERE nome_credor IS NOT NULL AND btrim(nome_credor) <> '') / NULLIF(COUNT(*), 0), 0)
           ), now() FROM vw_pagamentos_ativos
    ON CONFLICT (conjunto) DO UPDATE SET registros=EXCLUDED.registros, ano_min=EXCLUDED.ano_min, ano_max=EXCLUDED.ano_max, maior_data_referencia=EXCLUDED.maior_data_referencia, qualidade=EXCLUDED.qualidade, calculado_em=EXCLUDED.calculado_em;

    INSERT INTO metadados_qualidade
    SELECT 'receitas', COUNT(*), MIN(ano), MAX(ano), NULL::date,
           jsonb_build_object(
               'previsao_positiva_pct', COALESCE(100.0 * COUNT(*) FILTER (WHERE valor_previsto > 0) / NULLIF(COUNT(*), 0), 0),
               'categoria_preenchida_pct', COALESCE(100.0 * COUNT(*) FILTER (WHERE categoria_economica IS NOT NULL AND btrim(categoria_economica) <> '') / NULLIF(COUNT(*), 0), 0)
           ), now() FROM vw_receitas_ativas
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
