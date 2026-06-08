"""
scripts/extract_neo.py
Extrai dados de asteroides próximos à Terra via NASA NeoWs API e salva como JSON bruto.
"""

import json
import logging
import os
from datetime import datetime, timedelta

import requests

logger = logging.getLogger(__name__)

NASA_NEO_URL = "https://api.nasa.gov/neo/rest/v1/feed"


def extract_nasa_neo(output_dir: str, **context) -> str:
    """
    Consulta a NASA NeoWs API para a janela de 7 dias a partir da data de execução.
    A chave de API deve ser definida na variável de ambiente NASA_API_KEY.
    Caso não esteja configurada, usa DEMO_KEY (limitado a 30 req/hora).

    Returns:
        Caminho do arquivo JSON bruto salvo.
    """
    os.makedirs(output_dir, exist_ok=True)

    api_key      = os.environ.get("NASA_API_KEY", "DEMO_KEY")
    logical_date = context.get("logical_date") or datetime.utcnow()

    start_date = logical_date.strftime("%Y-%m-%d")
    end_date   = (logical_date + timedelta(days=7)).strftime("%Y-%m-%d")

    params = {
        "start_date": start_date,
        "end_date":   end_date,
        "api_key":    api_key,
    }

    logger.info(
        "Consultando NASA NeoWs API | janela: %s -> %s", start_date, end_date
    )

    try:
        response = requests.get(NASA_NEO_URL, params=params, timeout=30)
        response.raise_for_status()
    except requests.exceptions.RequestException as e:
        logger.error("Falha ao consultar NASA NeoWs API: %s", e)
        raise

    data = response.json()
    data["_ingestion_ts"] = datetime.utcnow().isoformat()
    data["_source"]       = "nasa_neows"

    timestamp   = datetime.utcnow().strftime("%Y%m%d_%H%M%S")
    output_path = os.path.join(output_dir, f"neo_raw_{timestamp}.json")

    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2)

    logger.info("NEO raw salvo em: %s | total de objetos: %s",
                output_path, data.get("element_count", "?"))

    context["ti"].xcom_push(key="neo_raw_path", value=output_path)

    return output_path
