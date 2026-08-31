-- Inclui deputados estaduais no mesmo modelo comparativo de despesas parlamentares.
ALTER TABLE fatos_despesas_parlamentares
    DROP CONSTRAINT IF EXISTS fatos_despesas_parlamentares_cargo_check;
ALTER TABLE fatos_despesas_parlamentares
    ADD CONSTRAINT fatos_despesas_parlamentares_cargo_check
    CHECK (cargo IN ('deputado_federal', 'deputado_estadual', 'senador'));

ALTER TABLE parlamentares_lote
    DROP CONSTRAINT IF EXISTS parlamentares_lote_cargo_check;
ALTER TABLE parlamentares_lote
    ADD CONSTRAINT parlamentares_lote_cargo_check
    CHECK (cargo IN ('deputado_federal', 'deputado_estadual', 'senador'));
