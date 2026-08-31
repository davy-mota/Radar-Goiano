# Radar Goiano - backend

## Configuração

1. Crie um ambiente virtual e instale `requirements.txt`.
2. Copie `.env.example` para `.env` na raiz do projeto.
3. Ajuste `DATABASE_URL` e, se necessário, `CORS_ORIGINS`. No desenvolvimento local,
   mantenha tanto `http://localhost:5173` quanto `http://127.0.0.1:5173` autorizados.

Para iniciar a API a partir da pasta `backend`:

```powershell
uvicorn main:app --reload
```

Para gerar os caches e sincronizá-los com o frontend:

```powershell
python gerar_cache.py
```

Depois de importar ou alterar dados no PostgreSQL, atualize os indicadores materializados do painel de qualidade:

```powershell
python atualizar_metadados.py
```

A estrutura necessária é criada por `migrations/006_metadados_qualidade.sql`. O endpoint `GET /api/metadados` lê essa estrutura pré-calculada para evitar agregações completas em cada requisição.

## Cargas auditadas

Execute novas importações pelo executor central para registrar início, término, duração, resultado e quantidade final de registros:

```powershell
python executar_carga.py pagamentos
python executar_carga.py receitas
python executar_carga.py contratos
python executar_carga.py folha
python executar_carga.py diarias
```

O executor aceita apenas esses cinco nomes. Uma carga bem-sucedida também atualiza os metadados de qualidade. A estrutura do histórico é criada por `migrations/007_historico_cargas.sql` e consultada em `GET /api/cargas`.

## Cargas versionadas por exercício

Cota parlamentar de deputados federais (CEAP) e de senadores (CEAPS) por Goiás, um exercício por vez, com lote isolado (`migrations/018_despesas_parlamentares.sql`):

```powershell
python carga_deputados.py --ano 2026
python carga_senadores.py --ano 2026
```

Cada execução cria um lote `preparando`, valida (rejeita se não houver registros ou soma nula) e só então ativa, arquivando o lote anterior do mesmo exercício — outros exercícios não são afetados.
