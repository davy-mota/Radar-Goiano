CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_receitas_ano_mes
ON receitas_estaduais (ano_exercicio, mes_exercicio);

CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_receitas_ano_categoria
ON receitas_estaduais (ano_exercicio, categoria_receita);
