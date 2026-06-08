"""
scripts/analytics.py
Executa as 5 consultas analíticas SQL no Oracle e salva os resultados em JSON.
"""

import json
import logging
import os
from datetime import datetime

import oracledb as cx_Oracle

logger = logging.getLogger(__name__)


def _get_connection() -> cx_Oracle.Connection:
    user     = os.environ["ORACLE_USER"]
    password = os.environ["ORACLE_PASSWORD"]
    host     = os.environ.get("ORACLE_HOST", "oracle.fiap.com.br")
    port     = int(os.environ.get("ORACLE_PORT", "1521"))
    sid      = os.environ.get("ORACLE_SID", "ORCL")
    return cx_Oracle.connect(user=user, password=password, host=host, port=port, sid=sid)


# ─── As 5 consultas analíticas ────────────────────────────────────────────────

QUERIES = {

    # 1. Distribuição dos registros da ISS por hora do dia (UTC)
    "q1_iss_por_hora": """
        SELECT
            HORA_UTC                        AS hora_utc,
            COUNT(*)                        AS total_registros,
            ROUND(AVG(LATITUDE),  4)        AS lat_media,
            ROUND(AVG(LONGITUDE), 4)        AS lon_media
        FROM ISS_POSITIONS
        GROUP BY HORA_UTC
        ORDER BY HORA_UTC
    """,

    # 2. Top 10 NEOs mais próximos da Terra (menor distância registrada)
    "q2_neo_mais_proximos": """
        SELECT
            NEO_ID,
            NOME,
            ROUND(DISTANCIA_KM, 0)          AS distancia_km,
            ROUND(VELOCIDADE_KMS, 3)        AS velocidade_kms,
            ROUND(DIAMETRO_KM_AVG * 1000, 1) AS diametro_metros,
            CASE IS_PERIGOSO
                WHEN 1 THEN 'SIM'
                ELSE 'NÃO'
            END                             AS potencialmente_perigoso,
            TO_CHAR(DATA_REFERENCIA, 'YYYY-MM-DD') AS data_referencia
        FROM NEO_OBJECTS
        ORDER BY DISTANCIA_KM ASC
        FETCH FIRST 10 ROWS ONLY
    """,

    # 3. Distância média, mínima e máxima dos NEOs agrupada por mês
    "q3_distancia_mensal_neo": """
        SELECT
            TO_CHAR(DATA_REFERENCIA, 'YYYY-MM')  AS mes_referencia,
            COUNT(*)                              AS total_neos,
            ROUND(AVG(DISTANCIA_KM), 0)           AS distancia_media_km,
            ROUND(MIN(DISTANCIA_KM), 0)           AS distancia_minima_km,
            ROUND(MAX(DISTANCIA_KM), 0)           AS distancia_maxima_km
        FROM NEO_OBJECTS
        GROUP BY TO_CHAR(DATA_REFERENCIA, 'YYYY-MM')
        ORDER BY mes_referencia
    """,

    # 4. Distribuição da ISS por quadrante geográfico com latitudes extremas
    "q4_iss_por_quadrante": """
        SELECT
            QUADRANTE,
            COUNT(*)                    AS total_registros,
            ROUND(MIN(LATITUDE),  4)    AS lat_minima,
            ROUND(MAX(LATITUDE),  4)    AS lat_maxima,
            ROUND(MIN(LONGITUDE), 4)    AS lon_minima,
            ROUND(MAX(LONGITUDE), 4)    AS lon_maxima
        FROM ISS_POSITIONS
        GROUP BY QUADRANTE
        ORDER BY total_registros DESC
    """,

    # 5. Ranking dos NEOs potencialmente perigosos por velocidade
    "q5_ranking_neos_perigosos": """
        SELECT
            NEO_ID,
            NOME,
            ROUND(VELOCIDADE_KMS, 3)         AS velocidade_kms,
            ROUND(DISTANCIA_KM / 384400, 4)  AS distancia_em_distancias_lunares,
            ROUND(DIAMETRO_KM_AVG * 1000, 1) AS diametro_metros,
            ROUND(MAGNITUDE, 2)              AS magnitude,
            TO_CHAR(DATA_REFERENCIA, 'YYYY-MM-DD') AS data_referencia,
            RANK() OVER (ORDER BY VELOCIDADE_KMS DESC) AS ranking_velocidade
        FROM NEO_OBJECTS
        WHERE IS_PERIGOSO = 1
        ORDER BY VELOCIDADE_KMS DESC
    """,
}


def run_analytics(**context) -> None:
    """
    Executa todas as queries analíticas e persiste os resultados em JSON.
    """
    logger.info("Conectando ao Oracle para consultas analíticas...")
    conn   = _get_connection()
    cursor = conn.cursor()

    results = {}
    for query_name, sql in QUERIES.items():
        logger.info("Executando: %s", query_name)
        try:
            cursor.execute(sql)
            columns = [col[0].lower() for col in cursor.description]
            rows    = [dict(zip(columns, row)) for row in cursor.fetchall()]
            results[query_name] = {"status": "ok", "rows": rows, "count": len(rows)}
            logger.info("  → %d linhas retornadas", len(rows))
        except cx_Oracle.Error as e:
            logger.error("Erro em %s: %s", query_name, e)
            results[query_name] = {"status": "error", "message": str(e)}

    cursor.close()
    conn.close()

    # Salva resultados em JSON para documentação / evidência
    output_path = "/opt/airflow/data/analytics_results.json"
    os.makedirs(os.path.dirname(output_path), exist_ok=True)
    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(
            {"executed_at": datetime.utcnow().isoformat(), "queries": results},
            f,
            indent=2,
            default=str,
        )

    logger.info("Resultados salvos em: %s", output_path)
    context["ti"].xcom_push(key="analytics_path", value=output_path)
