"""
DAG: orbital_monitoring_pipeline
Descrição: Pipeline de monitoramento orbital — coleta dados da ISS (Open Notify)
           e de asteroides próximos à Terra (NASA NeoWs), transforma e carrega
           no Oracle Database para análise.

Fluxo:
  extract_iss → extract_neo → transform_data → load_oracle → run_analytics

Disciplina: Big Data Architecture & Data Integration — FIAP Global Solution 2026
"""

from datetime import datetime, timedelta

from airflow import DAG
from airflow.operators.python import PythonOperator
from airflow.operators.empty import EmptyOperator

# ─── Importa as tarefas dos scripts auxiliares ────────────────────────────────
from scripts.extract_iss import extract_iss_position
from scripts.extract_neo import extract_nasa_neo
from scripts.transform   import transform_data
from scripts.load_oracle import load_oracle
from scripts.analytics   import run_analytics

# ─── Argumentos padrão da DAG ─────────────────────────────────────────────────
default_args = {
    "owner": "equipe_gs",
    "depends_on_past": False,
    "email_on_failure": False,
    "email_on_retry": False,
    "retries": 2,
    "retry_delay": timedelta(minutes=5),
}

# ─── Definição da DAG ─────────────────────────────────────────────────────────
with DAG(
    dag_id="orbital_monitoring_pipeline",
    description="Pipeline ISS + NASA NEO → Oracle",
    default_args=default_args,
    start_date=datetime(2026, 5, 25),
    schedule_interval="@hourly",      # executa a cada 1h para capturar posições da ISS
    catchup=False,
    tags=["global_solution", "espacial", "oracle"],
) as dag:

    # ── Task 0: Início ──────────────────────────────────────────────────────
    inicio = EmptyOperator(task_id="inicio")

    # ── Task 1: Extrai posição atual da ISS ─────────────────────────────────
    t1_iss = PythonOperator(
        task_id="extract_iss_position",
        python_callable=extract_iss_position,
        # passa o diretório de saída via op_kwargs
        op_kwargs={"output_dir": "/opt/airflow/data"},
        doc_md="""
        **Extração — ISS (Open Notify API)**
        - Endpoint: `http://api.open-notify.org/iss-now.json`
        - Sem autenticação necessária
        - Salva JSON bruto em `/data/iss_raw_<timestamp>.json`
        """,
    )

    # ── Task 2: Extrai asteroides próximos (NASA NeoWs) ─────────────────────
    t2_neo = PythonOperator(
        task_id="extract_nasa_neo",
        python_callable=extract_nasa_neo,
        op_kwargs={"output_dir": "/opt/airflow/data"},
        doc_md="""
        **Extração — NASA NeoWs API**
        - Endpoint: `https://api.nasa.gov/neo/rest/v1/feed`
        - Parâmetros: janela de 7 dias a partir da data de execução
        - Chave: variável de ambiente `NASA_API_KEY` (ou DEMO_KEY para testes)
        - Salva JSON bruto em `/data/neo_raw_<timestamp>.json`
        """,
    )

    # ── Task 3: Transformação e tratamento ──────────────────────────────────
    t3_transform = PythonOperator(
        task_id="transform_data",
        python_callable=transform_data,
        op_kwargs={"data_dir": "/opt/airflow/data"},
        doc_md="""
        **Transformação (pandas)**
        - Remove registros com lat/lon nulos
        - Converte timestamps Unix → datetime
        - Calcula quadrante geográfico da ISS
        - Normaliza unidades de distância (km)
        - Marca NEOs como perigosos/não perigosos
        - Salva CSVs limpos: `iss_clean.csv` e `neo_clean.csv`
        """,
    )

    # ── Task 4: Carga no Oracle ──────────────────────────────────────────────
    t4_load = PythonOperator(
        task_id="load_oracle",
        python_callable=load_oracle,
        op_kwargs={"data_dir": "/opt/airflow/data"},
        doc_md="""
        **Carga — Oracle Database**
        - Host: oracle.fiap.com.br | Porta: 1521 | SID: ORCL
        - Tabelas: ISS_POSITIONS, NEO_OBJECTS
        - Usa INSERT com checagem de duplicata por (timestamp, source)
        """,
    )

    # ── Task 5: Consultas analíticas SQL ────────────────────────────────────
    t5_analytics = PythonOperator(
        task_id="run_analytics",
        python_callable=run_analytics,
        doc_md="""
        **Consultas SQL analíticas (5 queries)**
        1. Registros da ISS por hora do dia
        2. Top 10 NEOs mais próximos
        3. Distância média mensal dos NEOs
        4. Distribuição da ISS por quadrante geográfico
        5. Ranking de NEOs potencialmente perigosos
        - Resultados salvos em `/data/analytics_results.json`
        """,
    )

    # ── Task 6: Fim ─────────────────────────────────────────────────────────
    fim = EmptyOperator(task_id="fim")

    # ─── Dependências ────────────────────────────────────────────────────────
    inicio >> [t1_iss, t2_neo] >> t3_transform >> t4_load >> t5_analytics >> fim
