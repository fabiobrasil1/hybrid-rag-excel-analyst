# Plano de arquitetura — hybrid-rag-excel-analyst

Documento de planejamento. Objetivo: RAG híbrido sobre Excel/CSV com **cálculos reais**, respostas ancoradas em execução e **separação clara** entre recuperação semântica e motor numérico.

Este documento prioriza **MVP simples**, **modularidade** e **fronteira explícita RAG ↔ engine de cálculo**.

---

## 1. Princípios do MVP

1. **Uma fonte de verdade numérica:** só números vindos do `ExecutionResult` (JSON tabular) entram na resposta final como fatos.
2. **RAG não calcula:** recuperação devolve **contexto de schema e domínio** (texto + referências a tabelas/colunas), nunca agrega dados nem “sabe” totais.
3. **Engine não interpreta linguagem natural:** recebe **SQL (ou plano já resolvido)** + **ligações a datasets**; valida e executa; devolve tabela/erro.
4. **Orquestração fina:** um módulo pequeno que encadeia `retrieve → (LLM opcional) → execute → compose`, sem misturar responsabilidades dentro dos outros pacotes.
5. **Menos infraestrutura:** um processo de API, armazenamento em disco (arquivos + metadados JSON), vector store embutido ou local; sem Postgres obrigatório no MVP.

---

## 2. Visão de arquitetura (MVP)

Três **subsystems** com contratos estáveis (tipos / JSON), não “uma bola de lama”:

```text
                    ┌─────────────────────────────────────┐
                    │           Orquestrador               │
                    │  (pipeline: pergunta → resposta)     │
                    └───────────┬────────────┬────────────┘
                                │            │
              RetrievalContext  │            │  ExecutionRequest
                                ▼            ▼
                    ┌───────────────┐   ┌──────────────────┐
                    │  Camada RAG   │   │ Engine de cálculo │
                    │ (só busca +   │   │ (só SQL/DuckDB +   │
                    │  contexto)    │   │  validação + run) │
                    └───────────────┘   └──────────────────┘
```

- **Camada RAG:** embeddings sobre **descrições de schema** (e opcionalmente notas do usuário). Saída: trechos ranqueados + **lista explícita de `table_id` / `column_id` candidatos** (nunca valores agregados).
- **Engine de cálculo:** DuckDB sobre arquivos materializados (CSV/Parquet ou tabelas registradas). Entrada: SQL + `dataset_id` + allowlist derivada do catálogo (e do retrieval). Saída: linhas/colunas + tipos + erro de execução.
- **LLM (MVP+):** único lugar que lê linguagem natural; consome `RetrievalContext` + subconjunto de schema; **produz SQL** (ou pede clarificação). Não substitui o engine: se o SQL for inválido ou violar allowlist, o engine recusa e o orquestrador re-tenta ou devolve erro legível.

**Regra de ouro:** o arquivo/módulo do **retriever** não importa DuckDB; o **engine** não importa o client de embeddings. O orquestrador importa ambos.

---

## 3. Modularidade (pacotes lógicos do MVP)

| Pacote / módulo | Responsabilidade | O que **não** faz |
|-----------------|------------------|-------------------|
| `ingest` | Upload, parse Excel/CSV, retorno `dict[str, DataFrame]` | Embeddings, SQL, LLM |
| `schema_analysis` | Perfis de coluna/tipo + estatísticas básicas → `TableProfile` | Execução de consultas do usuário |
| `insights` | Sinais estatísticos (IQR, top share, tendência simples) antes de qualquer LLM | NLU |
| `retrieval` (RAG) | Chunks a partir de `TableProfile`, embeddings, busca semântica simples | Executar consultas, chamar LLM |
| `execution` (engine) | `ExecutionPlan` validado → DuckDB; resultado tabular (`ExecutionResult`) | Embeddings, NLU |
| `llm` | Plano (JSON) + texto explicativo ancorado em resultados | Cálculo numérico |
| `orchestration` | Orquestra pipeline, agrega erros, limite de tokens, política de retry mínima | Parser de Excel, SQL engine |

Versões futuras podem trocar Chroma por pgvector ou o LLM por outro provedor **sem reescrever** `execution` nem `schema_analysis`.

---

## 4. Estrutura de pastas (MVP enxuto)

Manter monorepo simples até o segundo cliente (ex.: CLI separada):

```text
hybrid-rag-excel-analyst/
├── src/
│   └── excel_analyst/
│       ├── ingest/
│       ├── schema_analysis/
│       ├── execution/
│       ├── retrieval/
│       ├── insights/
│       ├── llm/
│       └── orchestration/
├── apps/
│   └── streamlit_app.py     # UI MVP (upload, preview, pergunta)
├── storage/                 # .gitignore: chroma / temporários de sessão
├── tests/
├── configs/
├── docs/
│   └── PLANO.md
└── pyproject.toml
```

O `streamlit_app` importa `orchestration` e os módulos de domínio; não contém regras de cálculo nem RAG embutidas.

---

## 5. Fluxo MVP (upload → resposta)

1. **Upload** → salvar arquivo → `ingest` gera tabelas + `catalog.json` (+ Parquet opcional).
2. **Indexação (RAG):** `retrieval` lê o catálogo, gera chunks, indexa com `dataset_id` nos metadados de cada vetor.
3. **Pergunta:** orquestrador chama `retrieve` com filtro `dataset_id`.
4. **Montagem de allowlist:** união das colunas/tabelas citadas no `RetrievalContext` + validação contra `catalog` completo (evita SQL em colunas inexistentes).
5. **LLM:** gera SQL usando **apenas** nomes permitidos (mensagem de sistema com lista fechada).
6. **Engine:** `execution` valida e roda no DuckDB; retorna JSON estritamente dos resultados.
7. **Composer (LLM ou template):** texto final usando só `ExecutionResult`; opcional no MVP mais pobre: resposta só com tabela JSON + uma frase fixa.

Itens **fora do MVP inicial:** UI rica, multi-tenant, cache distribuído, sandbox em container, BM25 híbrido.

---

## 6. Contrato entre RAG e engine (separação clara)

Definir cedo (tipos Pydantic ou equivalente):

- **`RetrievalContext`:** `chunks: list[str]`, `referenced_tables: list[str]`, `referenced_columns: list[tuple[table, col]]`, `scores`, `dataset_id`.
- **`ExecutionRequest`:** `dataset_id`, `sql: str`, `allowed_relations: set[str]` (views/tabelas DuckDB permitidas), `timeout_ms`, `max_rows`.
- **`ExecutionResult`:** `columns`, `rows`, `row_count`, `truncated: bool`, `error: str | null`.

O **orquestrador** é o único que transforma `RetrievalContext` em restrições do `ExecutionRequest`. O RAG **nunca** preenche `rows`; o engine **nunca** preenche `chunks`.

---

## 7. O que implementar primeiro (ordem recomendada)

| Ordem | Entrega | Por quê |
|-------|---------|--------|
| **1** | `ingest` + `catalog` + persistência em disco + teste com 1 CSV e 1 XLSX | Sem dados estruturados não há produto; catálogo é a base do resto. |
| **2** | `execution`: registrar Parquet/CSV no DuckDB, executar SQL fixo de teste, `ExecutionResult` serializado | Valida o coração “números reais” e o contrato de saída **sem** LLM nem vetores. |
| **3** | `apps/api`: upload + endpoint “execute SQL de teste” ou “query com SQL já conhecido” (só desenvolvimento) | Prova integração ponta a ponta; pode ser removido ou protegido depois. |
| **4** | `retrieval`: chunks do catálogo + store local + `retrieve` | RAG isolado; testável com pergunta fixa e assert nas colunas recuperadas. |
| **5** | `llm` + orquestração: NL → SQL com allowlist → `execution` → resposta | Fecha o loop híbrido com risco controlado. |
| **6** | Endurecer: limites de tempo/memória, remover endpoint de SQL livre em produção, composer com checagem de números | Segurança e qualidade. |

Implementar **engine antes do RAG** força o hábito correto: primeiro cálculo confiável, depois contexto para o modelo não “inventar” nomes de colunas sem validação.

---

## 8. Dependências sugeridas (MVP Python)

**Núcleo de dados e API**

| Dependência | Papel no MVP |
|-------------|----------------|
| `fastapi` | API HTTP, validação de schema de requests. |
| `uvicorn[standard]` | Servidor ASGI. |
| `pydantic` / `pydantic-settings` | Contratos e config (`Settings` com `.env`). |
| `python-dotenv` | Carregar variáveis locais (não commitadas). |

**Ingestão**

| Dependência | Papel |
|-------------|--------|
| `pandas` | Leitura/normalização; utilitário universal no MVP. |
| `openpyxl` | Excel `.xlsx` (engine do pandas). |
| `pyarrow` | Parquet intermedário (recomendado para DuckDB e reprodutibilidade). |

**Engine de cálculo**

| Dependência | Papel |
|-------------|--------|
| `duckdb` | SQL analítico local, bom desempenho em CSV/Parquet sem servidor separado. |

**RAG**

| Dependência | Papel |
|-------------|--------|
| `chromadb` | Vector store embutido, simples para MVP local (persistência em pasta). |
| `openai` | Embeddings + chat (ex.: `text-embedding-3-small` + modelo de chat); reduz código custom. |

**Alternativas conscientes**

- **Embeddings 100% locais:** `sentence-transformers` + Chroma — evita enviar dados para API, mas aumenta peso da imagem e RAM; bom para um milestone de privacidade.
- **Sem Chroma:** índice simples + `numpy` + busca por similaridade coseno em memória — só para datasets minúsculos e protótipo rápido.
- **API LLM:** trocar `openai` por cliente Anthropic ou Azure alterando só `llm/` se o contrato interno for estável.

**Dev / qualidade (recomendado desde o início)**

| Dependência | Papel |
|-------------|--------|
| `pytest` | Testes do catálogo, retrieval e engine. |
| `httpx` | Testes async da API FastAPI. |
| `ruff` | Linter/formatador rápido. |

Fixar versões no `pyproject.toml` ou `requirements.lock` quando o primeiro fluxo e2e estiver verde.

---

## 9. Desafios técnicos (recapitulação enxuta)

| Tema | Mitigação no MVP |
|------|-------------------|
| Alucinação numérica | Resposta só a partir de `ExecutionResult`; allowlist de identificadores SQL. |
| Excel irregular | MVP: primeira aba + cabeçalho na linha 0; refinamentos depois. |
| Segurança SQL | Allowlist de relações/colunas; sem SQL arbitrário exposto em produção. |
| RAG recuperar contexto errado | Metadado `dataset_id` em todo chunk; top-k baixo e validação contra catálogo. |

---

## 10. Evolução pós-MVP (sem mudar a fronteira)

- Retrieval híbrido (BM25 + denso), re-ranking.
- Sandbox em subprocesso/container; políticas de recurso.
- UI dedicada; multi-arquivo e joins.
- Validação automática de números na resposta natural vs JSON.

---

## 11. Módulo de ingestão de dados

**Objetivo:** ler Excel (`.xlsx`) e CSV, suportar **múltiplas abas**, devolver **DataFrames** por tabela, com API pequena e erros explícitos.

**Requisitos funcionais**

- `load_csv(path) -> pandas.DataFrame`
- `load_excel(path) -> dict[str, pandas.DataFrame]` — chave = nome da aba; ignora abas vazias sem cabeçalho útil.
- Funções puras onde possível; I/O isolado; validação de extensão e existência de arquivo.

**Tratamento de erros (básico)**

- Exceção dedicada `IngestError` (mensagem + `cause` opcional) para falhas de leitura, encoding, formato inesperado ou aba sem colunas.

**O que não faz:** inferência profunda de tipos (fica no módulo de schema), embeddings, LLM.

---

## 12. Módulo de análise de schema

**Objetivo:** transformar cada `DataFrame` em um **objeto estruturado** consumido pelo RAG e pelo LLM (somente metadados e estatísticas, não “respostas analíticas”).

**Deve identificar**

- Nome das colunas (como expostas pelo pandas após leitura).
- Tipo lógico: `numeric` | `categorical` | `datetime` | `text` | `unknown` (heurística sobre `dtype` + taxa de conversão).

**Estatísticas básicas (por coluna, quando aplicável)**

- `null_count`, `non_null_count`
- Numéricos: `mean`, `min`, `max` (somente se houver valores válidos)
- Categóricos: `unique_count`, `top_values` (top-k frequências)
- Datetime: `min`, `max` quando parseável

**Saída:** modelo Pydantic imutável em espírito (ex.: `TableProfile` com lista de `ColumnProfile`) serializável para JSON — alimenta `retrieval` (texto dos chunks) e prompts do LLM (allowlist de nomes).

**O que não faz:** agregações solicitadas pelo usuário (isso é **engine**).

---

## 13. Engine de consulta (cálculo real)

**Objetivo:** executar **média, soma, contagem, agrupamento, ordenação, top N, filtros** com resultados **100% derivados de pandas/DuckDB**.

**Desenho**

- Entrada preferencial: `ExecutionPlan` estruturado (agregações, `group_by`, `filters`, `order_by`, `limit`) validado contra allowlist de tabelas/colunas.
- Implementação MVP: **DuckDB** em memória registrando os DataFrames (`con.register(...)`); montagem de SQL a partir do plano — **sem** passar SQL livre vindo do usuário.
- O **LLM pode propor o plano** (interpretação), mas **nunca** materializa números: só o engine executa.

**Funções reutilizáveis (exemplos de responsabilidade)**

- `validate_plan(plan, allowlist) -> None` levanta `ExecutionError`
- `run_plan(con, plan) -> ExecutionResult` (colunas + linhas + `truncated`)

**O que não faz:** embeddings, busca semântica, narrativa.

---

## 14. Camada de RAG sobre metadados

**Objetivo:** dado uma pergunta, recuperar **trechos de texto** que descrevem colunas, tipos e estatísticas resumidas — para orientar **quais** campos usar na consulta.

**Inclui**

- Construção de documentos (um ou mais chunks por tabela/coluna) a partir de `TableProfile`.
- Embeddings + armazenamento local (ex.: Chroma persistente em pasta de trabalho da sessão Streamlit).
- Busca semântica simples (`top_k`).

**Saída:** `RetrievalContext` (textos + metadados opcionais de colunas citadas) — **sem** números analíticos além dos já pré-computados no perfil (counts, mean etc. são metadados descritivos do dataset, não resposta à pergunta ad-hoc).

**O que não faz:** executar SQL/pandas da pergunta do usuário.

---

## 15. Lógica principal (orquestração)

**Separação obrigatória**

| Fase | Responsabilidade |
|------|------------------|
| **Interpretação** | Classificar tipo de pergunta (`cálculo`, `comparação`, `insight`, `lookup`, …); opcionalmente chamar LLM para **plano**; chamar RAG para **contexto** de schema. |
| **Execução** | Validar plano → `execution.run_plan` → `ExecutionResult` (fonte da verdade numérica). |
| **Resposta** | Opcionalmente LLM **só** redige texto a partir do JSON/tabular do passo anterior; se não houver LLM, exibir tabela + labels. |

**Fluxo lógico**

1. Receber pergunta + `dataset_id` / tabela ativa.
2. `retrieve` (RAG) → contexto de colunas prováveis.
3. `classify_intent` (heurística e/ou LLM **sem** cálculo).
4. Se necessário: `build_execution_plan` (LLM com JSON schema + allowlist).
5. `execute` → resultado tabular.
6. `compose_answer` (LLM restrito ao resultado) **ou** resposta estruturada na UI.

**Regras:** números da resposta final = números do `ExecutionResult` (e estatísticas de insights calculadas no módulo `insights`, não “chutadas” pelo LLM).

---

## 16. Módulo de insights

**Objetivo:** destacar padrões simples com **sinais estatísticos calculados** (pandas/numpy), depois opcionalmente pedir ao LLM uma **explicação** que não introduza novos números.

**Sinais (exemplos)**

- Maiores / menores valores por coluna numérica.
- Concentração: top share (soma dos top-k / soma total).
- Tendência simples: inclinação OLS em série temporal se houver coluna datetime + numérica; caso contrário omitir com motivo explícito no objeto.
- Outliers: método IQR (`Q1 - 1.5*IQR`, `Q3 + 1.5*IQR`) com contagem e exemplos limitados.

**Saída:** objeto estruturado `InsightSignals` (listas, contagens, valores atuais) passível de serialização JSON para o compositor de texto.

**LLM:** recebe o JSON dos sinais; instrução do sistema: não inventar métricas novas; parafrasear e priorizar o que está no JSON.

---

## 17. Interface Streamlit (MVP)

**Telas / componentes**

- Upload (Excel/CSV).
- Seletor de aba (quando Excel multi-abas).
- Preview (`st.dataframe` com limite de linhas).
- Painel de schema (tipos + estatísticas resumidas).
- Campo de pergunta em linguagem natural.
- Área de resposta: tabela numérica + texto explicativo (quando LLM disponível).

**Layout:** simples, colunas `st.columns` para preview vs schema se útil.

**Regras na UI:** deixar explícito quando a resposta numérica veio do engine (sempre) e quando o texto é apenas interpretação.

---

*Última atualização: plano estendido com ingestão, schema, engine, RAG, orquestração, insights e Streamlit.*
