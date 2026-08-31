-- O perfil do Governador filtra folha_pagamento por cargo (52M linhas, sem índice
-- de apoio), o que levava a consulta a ~39s de full scan. Índice funcional sobre
-- LOWER(cargo) permite index scan para comparações de cargo (Governador, Vice-Governador
-- e futuras autoridades por cargo nominal).
DROP INDEX CONCURRENTLY IF EXISTS idx_folha_cargo_lower;

CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_folha_cargo_lower
ON folha_pagamento (LOWER(cargo));
