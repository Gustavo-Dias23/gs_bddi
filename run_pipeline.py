"""
run_pipeline.py
Executa o pipeline completo sem Apache Airflow.
Uso: python run_pipeline.py
Requer: .env com ORACLE_USER, ORACLE_PASSWORD (e opcionalmente NASA_API_KEY)
"""

import logging
import os
import sys
from datetime import datetime
from pathlib import Path

# Carrega .env se existir
try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    pass

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    handlers=[logging.StreamHandler(sys.stdout)],
)
logger = logging.getLogger("run_pipeline")

DATA_DIR = "data"


class FakeTI:
    """Simula o TaskInstance do Airflow para uso do XCom."""
    _store: dict = {}

    def xcom_push(self, key: str, value, **kw):
        self._store[key] = value
        logger.info("  XCom push -> %s = %s", key, value)

    def xcom_pull(self, key: str, **kw):
        return self._store.get(key)


def separator(title: str):
    logger.info("=" * 60)
    logger.info("  %s", title)
    logger.info("=" * 60)


def main():
    ti = FakeTI()
    ctx = {"ti": ti}
    start = datetime.utcnow()

    # ── Task 1: Extract ISS ──────────────────────────────────────
    separator("TASK 1 -extract_iss_position")
    from dags.scripts.extract_iss import extract_iss_position
    iss_path = extract_iss_position(output_dir=DATA_DIR, **ctx)
    logger.info("ISS raw salvo: %s", iss_path)

    # ── Task 2: Extract NEO ──────────────────────────────────────
    separator("TASK 2 -extract_nasa_neo")
    from dags.scripts.extract_neo import extract_nasa_neo
    neo_path = extract_nasa_neo(output_dir=DATA_DIR, **ctx)
    logger.info("NEO raw salvo: %s", neo_path)

    # ── Task 3: Transform ────────────────────────────────────────
    separator("TASK 3 -transform_data")
    from dags.scripts.transform import transform_data
    transform_data(data_dir=DATA_DIR, **ctx)
    logger.info("Transformacao concluida.")

    # ── Task 4: Load Oracle ──────────────────────────────────────
    separator("TASK 4 -load_oracle")
    if not os.environ.get("ORACLE_USER"):
        logger.warning("ORACLE_USER nao definido -pulando carga no Oracle.")
        logger.warning("Preencha o arquivo .env e rode novamente para carregar.")
    else:
        try:
            from dags.scripts.load_oracle import load_oracle
            load_oracle(data_dir=DATA_DIR, **ctx)
            logger.info("Carga no Oracle concluida.")
        except Exception as e:
            logger.error("Erro na carga Oracle: %s", e)
            logger.error("Verifique conexao de rede com oracle.fiap.com.br (VPN/FIAP)")

    # ── Task 5: Analytics ────────────────────────────────────────
    separator("TASK 5 -run_analytics")
    if not os.environ.get("ORACLE_USER"):
        logger.warning("ORACLE_USER nao definido -pulando analytics.")
    else:
        try:
            from dags.scripts.analytics import run_analytics
            run_analytics(**ctx)
            logger.info("Analytics concluido.")
        except Exception as e:
            logger.error("Erro no analytics: %s", e)

    # ── Resumo ───────────────────────────────────────────────────
    elapsed = (datetime.utcnow() - start).total_seconds()
    separator("PIPELINE CONCLUIDO")
    logger.info("Tempo total: %.1f segundos", elapsed)
    logger.info("Arquivos em %s/:", DATA_DIR)
    for f in sorted(Path(DATA_DIR).iterdir()):
        logger.info("  %s", f.name)


if __name__ == "__main__":
    main()
