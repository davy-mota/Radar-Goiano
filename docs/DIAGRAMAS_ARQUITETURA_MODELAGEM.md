# Diagramas de arquitetura e modelagem do Radar Goiano

## 1. Finalidade e método

Este documento representa a arquitetura **realmente implementada** no Radar
Goiano em 2 de novembro de 2026. Os diagramas foram derivados dos seguintes
artefatos versionados:

- `compose.prod.yml`, `Dockerfile.api`, `Dockerfile.web` e `Dockerfile.carga`;
- `deploy/Caddyfile`, `deploy/nginx.conf` e `scripts/deploy_vps.sh`;
- `backend/main.py`, `backend/controllers/` e os carregadores `carga_*.py`;
- migrações SQL de `backend/migrations/008` a `020`;
- componentes React e chamadas HTTP em `frontend/radar-front/src/`.

Não são incluídos serviços planejados ou relações que não existam no código ou
no banco. Relações lógicas sem chave estrangeira são identificadas como tal.

Para uso no TCC, a legenda recomendada é: **Fonte: elaborado pelo autor com base
na implementação do Radar Goiano (2026).**

## 2. Diagrama de contexto do sistema

**Figura 1 — Contexto, usuários e fontes externas.**

```mermaid
flowchart LR
    CIDADAO["Cidadão / pesquisador"]
    ADMIN["Administrador de dados"]
    RADAR["Radar Goiano<br/>portal de análise e transparência"]

    GOIAS["Portal de Dados Abertos<br/>e Transparência de Goiás"]
    CAMARA["Câmara dos Deputados<br/>CEAP"]
    SENADO["Senado Federal<br/>CEAPS"]
    ALEGO["Assembleia Legislativa<br/>Verba Indenizatória"]
    IBGE["IBGE<br/>municípios, população e malha"]
    VLIBRAS["VLibras<br/>tradução para Libras"]

    CIDADAO -->|"consulta painéis e exporta CSV"| RADAR
    ADMIN -->|"executa cargas, valida e ativa versões"| RADAR
    GOIAS -->|"CSV / ZIP / catálogo CKAN"| RADAR
    CAMARA -->|"arquivo anual CEAP"| RADAR
    SENADO -->|"CSV CEAPS e cadastro"| RADAR
    ALEGO -->|"API JSON mensal"| RADAR
    IBGE -->|"API e GeoJSON"| RADAR
    RADAR -->|"carrega widget oficial"| VLIBRAS
```

O usuário público não grava dados. A administração é um processo operacional
separado, executado somente durante cargas, migrações e implantação.

## 3. Arquitetura de implantação em produção

**Figura 2 — Contêineres, fronteiras de rede e publicação.**

```mermaid
flowchart TB
    subgraph INTERNET["Internet"]
        USER["Navegador"]
        GH["GitHub Actions"]
        EDGE["Cloudflare<br/>DNS, TLS, WAF e mitigação DDoS"]
        VLIB["vlibras.gov.br / jsDelivr"]
    end

    subgraph VPS["Droplet DigitalOcean — rede Docker radar"]
        TUNNEL["cloudflared<br/>conexão somente de saída"]
        CADDY["Caddy<br/>gateway interno :80"]
        NGINX["Nginx + React<br/>web :80"]
        API["FastAPI + Uvicorn<br/>api :8000"]
        DB[("PostgreSQL 18<br/>banco :5432")]
        CONFIG["configurador<br/>perfil maintenance"]
        LOAD["carga<br/>perfil maintenance"]
        LOOPBACK["127.0.0.1:8080<br/>diagnóstico local"]
    end

    USER -->|"HTTPS"| EDGE
    EDGE -->|"Cloudflare Tunnel"| TUNNEL
    TUNNEL -->|"HTTP interno"| CADDY
    CADDY --> NGINX
    NGINX -->|"arquivos React e JSON"| USER
    NGINX -->|"/backend/*"| API
    API -->|"radar_api: somente leitura"| DB
    CONFIG -->|"cria/atualiza papel radar_api"| DB
    LOAD -->|"conta administrativa durante a carga"| DB
    CADDY --- LOOPBACK
    GH -->|"SSH restrito + deploy_vps.sh"| VPS
    USER -->|"widget acessível"| VLIB

    classDef ephemeral stroke-dasharray: 6 4;
    class CONFIG,LOAD ephemeral;
```

Os serviços `configurador` e `carga` pertencem ao perfil `maintenance`: são
criados sob demanda e removidos ao terminar. PostgreSQL, API e aplicação não
publicam portas no IP externo. A única porta de administração do firewall é SSH,
restrita ao IP autorizado; `127.0.0.1:8080` não aceita conexões externas.

## 4. Componentes de software e caminhos de consulta

**Figura 3 — Relação entre interface, cache, API e banco.**

```mermaid
flowchart LR
    subgraph FRONT["Frontend React"]
        APP["App.jsx<br/>navegação, tema e acessibilidade"]
        STATIC["Painéis por cache<br/>Visão Geral, Contratos,<br/>Folha e Diárias"]
        DYNAMIC["Painéis dinâmicos<br/>Despesas, Fiscal, Políticas,<br/>Repasses, Emendas, Alertas,<br/>Qualidade e Parlamentares"]
    end

    subgraph WEB["Nginx"]
        JSON["/dados/*.json<br/>e GeoJSON"]
        PROXY["proxy /backend"]
        CONTROL["CSP, rate limiting,<br/>cache GET e cabeçalhos"]
    end

    subgraph BACK["FastAPI"]
        ROUTES["controllers/rotas_*.py"]
        HEALTH["/health"]
        DBACCESS["database.py / SQLAlchemy"]
    end

    subgraph DATA["PostgreSQL"]
        ACTIVE["views *_ativas"]
        MATERIALIZED["mv_despesas_execucao_mensal"]
        LEGACY["contratos_licitacoes<br/>folha_pagamento<br/>diarias_passagens"]
        META["metadados_qualidade<br/>historico_cargas"]
    end

    APP --> STATIC
    APP --> DYNAMIC
    STATIC --> JSON
    DYNAMIC --> PROXY
    PROXY --> CONTROL --> ROUTES
    HEALTH --> DBACCESS
    ROUTES --> DBACCESS
    DBACCESS --> ACTIVE
    DBACCESS --> MATERIALIZED
    DBACCESS --> LEGACY
    DBACCESS --> META
```

Essa divisão explica por que algumas telas dependem de regeneração de cache e
novo build, enquanto outras refletem imediatamente a versão ativa no banco.

## 5. Fluxo de ingestão, validação e publicação

**Figura 4 — Pipeline de dados auditável.**

```mermaid
flowchart TD
    SOURCE["Catálogo ou API oficial"]
    DISCOVER["Descobrir recursos publicados"]
    DOWNLOAD["Baixar recurso<br/>e calcular SHA-256"]
    PREPARE["Criar versão/lote<br/>status: preparando"]
    TRANSFORM["Normalizar esquema,<br/>tipos, datas e textos"]
    LOAD["Inserir fatos em blocos"]
    VALIDATE{"Validações bloqueantes<br/>aprovadas?"}
    REJECT["status: rejeitada<br/>versão ativa preservada"]
    READY["status: validada"]
    REVIEW["Revisar métricas,<br/>cobertura e fonte"]
    ACTIVATE["Ativação transacional"]
    ARCHIVE["versão/lote anterior<br/>status: arquivado"]
    VIEWS["views *_ativas"]
    AGG["metadados de qualidade e<br/>agregação materializada"]
    API2["API e caches públicos"]

    SOURCE --> DISCOVER --> DOWNLOAD --> PREPARE --> TRANSFORM --> LOAD --> VALIDATE
    VALIDATE -->|"não"| REJECT
    VALIDATE -->|"sim"| READY --> REVIEW --> ACTIVATE
    ACTIVATE --> ARCHIVE
    ACTIVATE --> VIEWS
    ACTIVATE --> AGG
    VIEWS --> API2
    AGG --> API2
```

A camada financeira usa uma versão global. Execução classificada, repasses,
emendas e despesas parlamentares usam lotes próprios. Em ambos os casos, a
versão anterior permanece disponível para reversão e a troca de estado ocorre em
transação.

## 6. Sequência de uma atualização financeira

**Figura 5 — Separação entre preparar e ativar.**

```mermaid
sequenceDiagram
    actor Operador
    participant Fonte as Catálogo oficial
    participant Carga as carga_financeira_versionada.py
    participant DB as PostgreSQL
    participant Ativador as ativar_versao.py
    participant API as FastAPI

    Operador->>Carga: iniciar reconstrução
    Carga->>DB: INSERT versão (preparando)
    loop Cada recurso oficial
        Carga->>Fonte: consultar e baixar CSV/ZIP
        Fonte-->>Carga: bytes + metadados
        Carga->>DB: recurso, hash e fatos
    end
    Carga->>DB: validar meses, anos, valores e sobreposições
    alt validação falha
        Carga->>DB: status = rejeitada
        API->>DB: continua lendo versão ativa anterior
    else validação aprovada
        Carga->>DB: status = validada
        Operador->>Ativador: ativar ID após revisão
        Ativador->>Fonte: verificar estabilidade dos recursos
        Ativador->>DB: arquivar ativa + ativar nova (transação)
        Ativador->>DB: atualizar qualidade e visão materializada
        API->>DB: views passam a servir a nova versão
    end
```

Não existe ativação automática no fim da carga financeira. Essa decisão reduz o
risco de publicar uma reconstrução sem revisão das métricas.

## 7. Modelo de dados financeiro versionado

**Figura 6 — Entidades da camada financeira principal.**

```mermaid
erDiagram
    VERSOES_DADOS ||--o{ RECURSOS_INGESTAO : possui
    VERSOES_DADOS ||--o{ FATOS_EMPENHOS : versiona
    VERSOES_DADOS ||--o{ FATOS_LIQUIDACOES : versiona
    VERSOES_DADOS ||--o{ FATOS_PAGAMENTOS : versiona
    VERSOES_DADOS ||--o{ FATOS_RECEITAS : versiona
    RECURSOS_INGESTAO ||--o{ FATOS_EMPENHOS : origina
    RECURSOS_INGESTAO ||--o{ FATOS_LIQUIDACOES : origina
    RECURSOS_INGESTAO ||--o{ FATOS_PAGAMENTOS : origina
    RECURSOS_INGESTAO ||--o{ FATOS_RECEITAS : origina

    VERSOES_DADOS {
        bigint id PK
        varchar status
        timestamptz iniciado_em
        timestamptz finalizado_em
        jsonb metricas
        text observacao
    }
    RECURSOS_INGESTAO {
        bigint id PK
        bigint versao_id FK
        varchar conjunto
        uuid recurso_ckan_id
        text nome
        text url
        char sha256
        bigint registros
    }
    FATOS_EMPENHOS {
        bigint id PK
        bigint versao_id FK
        bigint recurso_id FK
        integer ano_exercicio
        smallint mes
        text numero_empenho
        numeric valor_empenhado
        char chave_conteudo
    }
    FATOS_LIQUIDACOES {
        bigint id PK
        bigint versao_id FK
        bigint recurso_id FK
        integer ano_exercicio
        smallint mes
        text numero_empenho
        numeric valor_liquidado
        char chave_conteudo
    }
    FATOS_PAGAMENTOS {
        bigint id PK
        bigint versao_id FK
        bigint recurso_id FK
        integer ano_exercicio
        smallint mes
        text numero_empenho
        text documento_credor
        numeric valor_pago
        char chave_conteudo
    }
    FATOS_RECEITAS {
        bigint id PK
        bigint versao_id FK
        bigint recurso_id FK
        integer ano
        smallint mes
        text codigo_natureza
        numeric valor_previsto
        numeric valor_realizado
        char chave_conteudo
    }
```

As quatro views `vw_empenhos_ativos`, `vw_liquidacoes_ativas`,
`vw_pagamentos_ativos` e `vw_receitas_ativas` filtram fatos pela única versão com
status `ativa`. Empenho, liquidação e pagamento compartilham identificadores
publicados, mas não possuem chave estrangeira direta: os grãos e a qualidade dos
identificadores da fonte não garantem relação linha a linha.

## 8. Modelo dos domínios analíticos por lote

**Figura 7 — Lotes independentes e dimensão municipal.**

```mermaid
erDiagram
    LOTES_EXECUCAO_ORCAMENTARIA ||--o{ FATOS_EXECUCAO_ORCAMENTARIA : contem
    LOTES_REPASSES ||--o{ FATOS_REPASSES : contem
    LOTES_EMENDAS ||--o{ FATOS_EMENDAS : contem
    LOTES_DESPESAS_PARLAMENTARES ||--o{ FATOS_DESPESAS_PARLAMENTARES : contem
    LOTES_DESPESAS_PARLAMENTARES ||--o{ PARLAMENTARES_LOTE : cadastra
    MUNICIPIOS_IBGE ||--o{ POPULACOES_MUNICIPAIS : possui
    MUNICIPIOS_IBGE o|--o{ ALIASES_MUNICIPIOS : canoniza

    LOTES_EXECUCAO_ORCAMENTARIA {
        bigint id PK
        text status
        jsonb recursos
        jsonb metricas
    }
    FATOS_EXECUCAO_ORCAMENTARIA {
        bigint id PK
        bigint lote_id FK
        integer ano_exercicio
        integer mes
        text nome_funcao
        text nome_grupo
        numeric valor_pago
    }
    LOTES_REPASSES {
        bigint id PK
        text status
        jsonb recursos
        jsonb metricas
    }
    FATOS_REPASSES {
        bigint id PK
        bigint lote_id FK
        integer ano
        integer mes
        text municipio
        numeric credito_icms
        numeric credito_ipi
        numeric credito_ipva
    }
    LOTES_EMENDAS {
        bigint id PK
        text status
        integer ano
        jsonb recurso
        jsonb metricas
    }
    FATOS_EMENDAS {
        bigint id PK
        bigint lote_id FK
        integer ano
        text autor
        text municipio_origem
        text cnpj
        numeric valor_indicado
        numeric valor_pago
    }
    LOTES_DESPESAS_PARLAMENTARES {
        bigint id PK
        integer ano
        text status
        jsonb recursos
        jsonb metricas
    }
    FATOS_DESPESAS_PARLAMENTARES {
        bigint id PK
        bigint lote_id FK
        integer ano
        integer mes
        text cargo
        text parlamentar_codigo
        text categoria
        numeric valor_reembolsado
    }
    PARLAMENTARES_LOTE {
        bigint lote_id FK
        text cargo PK
        text parlamentar_codigo PK
        text parlamentar_nome
        text partido
    }
    MUNICIPIOS_IBGE {
        integer codigo_ibge PK
        text nome
        char uf
        text regiao_imediata
        text regiao_intermediaria
    }
    POPULACOES_MUNICIPAIS {
        integer codigo_ibge FK
        integer ano PK
        bigint populacao
        date referencia
    }
    ALIASES_MUNICIPIOS {
        text fonte PK
        text nome_origem PK
        integer codigo_ibge FK
        text metodo
    }
```

`vw_repasses_municipais_canonicos` liga repasses, aliases, município e população
para calcular valor por habitante. `vw_emendas_ativas` usa a mesma dimensão para
conciliar o município publicado na emenda. A tabela de parlamentares preserva
também pessoas cadastradas sem documento no período, evitando transformar
ausência na fonte em gasto zero.

## 9. Dados legados, caches e vínculos lógicos

**Figura 8 — Tabelas importadas e associações sem chave estrangeira.**

```mermaid
flowchart LR
    CONTRATOS[("contratos_licitacoes<br/>CNPJ, órgão, objeto e valor")]
    FOLHA[("folha_pagamento<br/>servidor, cargo e remuneração")]
    DIARIAS[("diarias_passagens<br/>servidor, destino e valor")]
    PAGAMENTOS[("vw_pagamentos_ativos<br/>credor, documento e pagamento")]

    CNPJ["normalização de CNPJ"]
    PERFIL["Perfil do Fornecedor"]
    GOV["Perfil do Governador"]
    CACHE["gerar_cache.py"]
    JSON["cache_contratos_*.json<br/>cache_folha_*.json<br/>cache_diarias_*.json<br/>cache_visao_geral_*.json"]

    PAGAMENTOS -.->|vínculo lógico por CNPJ válido| CNPJ
    CONTRATOS -.->|vínculo lógico por CNPJ válido| CNPJ
    CNPJ --> PERFIL
    FOLHA --> GOV
    DIARIAS --> GOV
    CONTRATOS --> CACHE
    FOLHA --> CACHE
    DIARIAS --> CACHE
    CACHE --> JSON
```

O Perfil do Fornecedor não relaciona registros por semelhança de nome. O vínculo
é calculado por CNPJ normalizado e válido, mas não existe uma chave estrangeira
entre contratos e pagamentos. Folha e diárias também permanecem em tabelas
independentes; o perfil do Governador aplica filtros funcionais explícitos.

## 10. Observabilidade, segurança e recuperação

**Figura 9 — Controles operacionais ao redor dos dados.**

```mermaid
flowchart TB
    LOAD["Carga ou ativação"] --> HIST[("historico_cargas")]
    LOAD --> QUALITY[("metadados_qualidade")]
    LOAD --> VERSION[("versões e lotes arquivados")]
    VERSION -->|"reversão transacional"| ACTIVE["camada ativa"]

    BACKUP["pg_dump -Fc + SHA-256"] --> RESTORE["procedimento de restauração"]
    DBROLE["radar_api<br/>SELECT e transação read-only"] --> ACTIVE
    ADMINROLE["radar_admin<br/>somente manutenção"] --> LOAD

    ACTIVE --> API["API"]
    API --> LIMIT["Nginx: rate limit,<br/>limites, timeout e cache"]
    LIMIT --> EDGE["Cloudflare: TLS, WAF,<br/>bots e DDoS"]
```

O backup físico e a reversão de versão resolvem problemas diferentes: a reversão
troca rapidamente a camada publicada; o dump permite recuperação diante de perda
ou corrupção do banco inteiro.

## 11. Limites dos diagramas

- Os diagramas mostram entidades e campos estruturantes, não todas as colunas.
- Views e índices aparecem quando alteram o comportamento arquitetural.
- O PostgreSQL contém versões arquivadas e rejeitadas; as APIs consultam apenas
  views ativas ou lotes ativos.
- A associação entre fornecedor, contrato e pagamento é lógica por documento e
  deliberadamente não foi desenhada como integridade referencial.
- O widget VLibras é um serviço externo de acessibilidade e não participa do
  processamento financeiro.
