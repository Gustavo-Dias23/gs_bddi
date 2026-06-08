"""
scripts/extract_iss.py
Extrai a posição atual da ISS via Open Notify API e salva como JSON bruto.
"""

import json
import logging
import os
from datetime import datetime

import requests

logger = logging.getLogger(__name__)

ISS_API_URL = "http://api.open-notify.org/iss-now.json"


def extract_iss_position(output_dir: str, **context) -> str:
    """
    Chama a Open Notify API e persiste o JSON bruto em disco.

    Returns:
        Caminho do arquivo salvo (usado como XCom para a próxima task).
    """
    os.makedirs(output_dir, exist_ok=True)

    logger.info("Consultando Open Notify API: %s", ISS_API_URL)

    try:
        response = requests.get(ISS_API_URL, timeout=10)
        response.raise_for_status()
    except requests.exceptions.RequestException as e:
        logger.error("Falha ao consultar ISS API: %s", e)
        raise

    data = response.json()

    # Adiciona metadados úteis para rastreabilidade
    data["_ingestion_ts"] = datetime.utcnow().isoformat()
    data["_source"]       = "open_notify_iss"

    timestamp = datetime.utcnow().strftime("%Y%m%d_%H%M%S")
    output_path = os.path.join(output_dir, f"iss_raw_{timestamp}.json")

    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2)

    logger.info("ISS raw salvo em: %s", output_path)

    # Empurra o caminho via XCom para a task de transformação
    context["ti"].xcom_push(key="iss_raw_path", value=output_path)

    return output_path
