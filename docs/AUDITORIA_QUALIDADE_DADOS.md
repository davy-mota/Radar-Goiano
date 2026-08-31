# Auditoria de Qualidade dos Dados

## 1. Escopo e data

Auditoria executada em 28 de agosto de 2026 sobre o PostgreSQL local do Radar Goiano. As verificações foram somente leitura e abrangeram volume, cobertura temporal, campos ausentes, valores atípicos, duplicidades potenciais e aderência dos extratores ao catálogo oficial.

Nenhuma tabela oficial foi apagada ou substituída. Uma recarga só deve ocorrer depois de o novo modelo passar pelas validações descritas neste documento e de existir backup recuperável.

## 2. Inventário local

| Conjunto | Registros | Cobertura observada | Tamanho aproximado |
|---|---:|---:|---:|
| Pagamentos | 4.079.506 | 2003–2025 | 1.277 MB |
| Receitas | 311.635 | 2006–2025 | 61 MB |
| Contratos | 61.447 | ano 0 e 1998–2025 | 20 MB |
| Folha | 52.105.021 | 2012–2025 | 9.643 MB |
| Diárias | 565.941 | 2011–2025 | 161 MB |

O disco possuía aproximadamente 24,4 GB livres no momento da auditoria. Esse espaço permite preservar e reconstruir pagamentos e receitas com cautela, mas não comporta com margem segura uma cópia integral adicional da folha de pagamento.

## 3. Achados

### 3.1 Pagamentos

- 1.970.562 grupos possuem a mesma combinação de ano, mês, empenho, documento, credor, data e valor;
- esses grupos representam 2.108.944 linhas excedentes em relação a uma ocorrência por chave de auditoria;
- 1.932.095 grupos aparecem exatamente duas vezes, padrão compatível com recarga duplicada;
- existem 782.260 documentos com quantidade de dígitos diferente de vazio, CPF ou CNPJ;
- foram encontrados quatro pagamentos acima de R$ 1 bilhão e dois valores negativos em 2019;
- a amostra oficial de 2024 possui 803.683 linhas, enquanto o banco possui 202.242, indicando também diferença de versão ou granularidade, não apenas duplicação.

A chave usada nesta auditoria é uma heurística e não autoriza exclusão automática: pagamentos diferentes podem compartilhar esses atributos. A fonte atual contém `NUMR_SEQUENCIAL_OP`, identificador que o esquema local descarta e que deve ser preservado na nova carga.

### 3.2 Receitas

- a fonte oficial de 2024 contém 10.652 linhas;
- o banco contém exatamente 21.304 linhas para 2024;
- no conjunto completo, 135.216 grupos repetidos representam 167.651 linhas excedentes;
- todas as 311.635 linhas estão sem data completa de arrecadação, porque a fonte oferece principalmente ano e mês;
- há valores negativos, que podem representar estornos e não devem ser removidos sem regra contábil.

O dobro exato na comparação de 2024 confirma duplicação decorrente da seleção simultânea de recursos sobrepostos ou de execução com `append`.

### 3.3 Folha, contratos e diárias

- a folha ocupa aproximadamente 9,6 GB e apresenta cerca de 320–340 mil linhas mensais entre 2012 e 2024, contra aproximadamente 165 mil em 2025;
- esse padrão exige comparação por identificador e semântica do dicionário antes de concluir duplicação, pois uma pessoa pode possuir múltiplas rubricas;
- contratos possuem 596 registros com ano zero, 30.783 sem data de assinatura e 18 valores negativos;
- diárias possuem um registro sem identificação de servidor nos campos auditados.

### 3.4 Incompatibilidade dos extratores

O catálogo de pagamentos foi atualizado em agosto de 2026 e já oferece arquivos de janeiro a julho de 2026. O extrator local seleciona nomes contendo 2025 e não acompanha dinamicamente o catálogo. Além disso, o arquivo atual usa campos como `VALR_OP`, `NUMR_SEQUENCIAL_OP`, `DATA_COMPLETA` e `NUMR_EMPENHO`, que não são reconhecidos integralmente pelo mapeamento legado.

O catálogo também publica conjuntos distintos para empenhos, liquidações e pagamentos. Somar essas etapas a partir de uma única planilha de pagamentos é semanticamente inadequado. A nova modelagem deve manter os três fatos separados e relacioná-los por chaves oficiais quando disponíveis.

## 4. Decisão

O problema principal não é a ausência de uma fonte oficial melhor. O Portal de Dados Abertos de Goiás continua sendo a fonte primária apropriada, mas a ingestão local usou seleção sobreposta, `append` e mapeamentos desatualizados.

As cargas legadas de pagamentos e receitas foram bloqueadas no executor auditável para impedir novas duplicações. A base atual permanece disponível temporariamente, acompanhada desta ressalva, até que a substituição segura seja concluída.

## 5. Plano de recarga segura

1. Criar tabelas separadas e versionadas para empenhos, liquidações, pagamentos e receitas.
2. Preservar identificadores oficiais e metadados do recurso: URL, identificador CKAN, data de modificação e hash SHA-256.
3. Selecionar recursos anuais independentes e mensais do ano corrente, excluindo arquivos consolidados sobrepostos.
4. Carregar em staging sem alterar as tabelas utilizadas pela aplicação.
5. Validar esquema, anos, meses, contagens, somatórios, unicidade do identificador oficial e cobertura esperada.
6. Comparar uma amostra por ano com o arquivo oficial e registrar as métricas no histórico de cargas.
7. Criar backup lógico ou tabelas de retenção antes da troca.
8. Efetuar a troca em transação curta e manter a versão anterior até a validação funcional do frontend.
9. Recalcular metadados e caches somente após a aprovação da nova versão.

## 6. Critérios mínimos para a troca

- nenhum recurso consolidado pode sobrepor recursos anuais ou mensais;
- nenhum identificador oficial pode ser descartado;
- divergências de contagem e somatório precisam ser explicadas por versão, granularidade ou regra contábil;
- valores negativos devem ser preservados e classificados como possíveis estornos;
- a aplicação deve distinguir valor empenhado, liquidado e pago por origem;
- a restauração da versão anterior deve ser testável antes da remoção definitiva.
