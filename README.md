# Pipeline de Monitoramento Orbital — BDDI Global Solution 2026

**Disciplina:** Big Data Architecture & Data Integration  
**Tema:** Indústria Espacial — Monitoramento de ISS e Asteroides

## 👥 Integrantes

| Nome | RM |
|------|----|
| Breno Silva | RM97864 |
| Enrico Marquez | RM99325 |
| Gustavo Dias | RM550820 |
| Joel Barros | RM550378 |
| Leonardo moreira | RM550988 |

---


---

## Arquitetura do Pipeline

```
[Open Notify API]   [NASA NeoWs API]
       |                  |
  extract_iss        extract_neo
       \                 /
        \               /
         transform_data          ← pandas (limpeza, tipagem, enriquecimento)
              |
         load_oracle              ← cx_Oracle → tabelas ISS_POSITIONS, NEO_OBJECTS
              |
         run_analytics            ← 5 queries SQL analíticas
```

## Fontes de Dados

| Fonte | URL | Autenticação |
|---|---|---|
| Open Notify (ISS) | http://api.open-notify.org/iss-now.json | Nenhuma |
| NASA NeoWs | https://api.nasa.gov/neo/rest/v1/feed | API Key gratuita |

## Como rodar localmente

```bash
# 1. Clone o repositório
git clone [<url>](https://github.com/Gustavo-Dias23/gs_bddi)

# 2. Configure credenciais
cp .env.example .env
# edite o .env com seu RM/senha Oracle e NASA_API_KEY

# 3. Suba o Airflow
docker compose up -d

# 4. Acesse http://localhost:8080
#    usuário: airflow | senha: airflow

# 5. Ative a DAG "orbital_monitoring_pipeline"
```

## Tabelas Oracle

- **ISS_POSITIONS** — posição, lat/lon, quadrante geográfico, hora UTC
- **NEO_OBJECTS** — id, nome, distância, velocidade, diâmetro, risco

## Consultas Analíticas

| # | Descrição |
|---|---|
| Q1 | Registros da ISS por hora do dia (UTC) |
| Q2 | Top 10 NEOs mais próximos da Terra |
| Q3 | Distância média/mín/máx dos NEOs por mês |
| Q4 | Distribuição da ISS por quadrante geográfico |
| Q5 | Ranking dos NEOs potencialmente perigosos por velocidade |

## Estrutura do Repositório

```
├── dags/
│   ├── orbital_monitoring_dag.py   ← DAG principal
│   └── scripts/
│       ├── extract_iss.py
│       ├── extract_neo.py
│       ├── transform.py
│       ├── load_oracle.py
│       └── analytics.py
├── data/                           ← arquivos intermediários (gitignore)
├── docker-compose.yml
├── requirements.txt
└── .env.example
```
