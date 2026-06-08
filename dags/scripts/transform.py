"""
scripts/transform.py
Transformação e tratamento dos dados brutos da ISS e NEOs usando pandas.
Gera dois CSVs limpos: iss_clean.csv e neo_clean.csv.
"""

import glob
import json
import logging
import os
from datetime import datetime

import pandas as pd

logger = logging.getLogger(__name__)


# ─── Helpers ──────────────────────────────────────────────────────────────────

def _get_quadrant(lat: float, lon: float) -> str:
    """Retorna o quadrante geográfico a partir de lat/lon."""
    ns = "N" if lat >= 0 else "S"
    ew = "E" if lon >= 0 else "W"
    return f"{ns}{ew}"


# ─── Transformação ISS ────────────────────────────────────────────────────────

def _transform_iss(data_dir: str) -> pd.DataFrame:
    """Lê todos os JSON brutos da ISS no diretório e retorna DataFrame limpo."""
    raw_files = sorted(glob.glob(os.path.join(data_dir, "iss_raw_*.json")))
    if not raw_files:
        raise FileNotFoundError(f"Nenhum arquivo iss_raw_*.json em {data_dir}")

    records = []
    for path in raw_files:
        with open(path, encoding="utf-8") as f:
            raw = json.load(f)

        pos = raw.get("iss_position", {})
        records.append({
            "timestamp_unix":   raw.get("timestamp"),
            "latitude":         pos.get("latitude"),
            "longitude":        pos.get("longitude"),
            "message":          raw.get("message"),
            "ingestion_ts":     raw.get("_ingestion_ts"),
            "source":           raw.get("_source"),
        })

    df = pd.DataFrame(records)

    # ── Limpeza ───────────────────────────────────────────────────────────────
    before = len(df)
    df.dropna(subset=["latitude", "longitude", "timestamp_unix"], inplace=True)
    logger.info("ISS: %d -> %d registros (removidos: %d nulos)",
                before, len(df), before - len(df))

    # ── Conversão de tipos ────────────────────────────────────────────────────
    df["latitude"]      = pd.to_numeric(df["latitude"],      errors="coerce")
    df["longitude"]     = pd.to_numeric(df["longitude"],     errors="coerce")
    df["timestamp_unix"] = pd.to_numeric(df["timestamp_unix"], errors="coerce")

    # ── Enriquecimento ────────────────────────────────────────────────────────
    df["timestamp_utc"] = pd.to_datetime(df["timestamp_unix"], unit="s", utc=True)
    df["hora_utc"]      = df["timestamp_utc"].dt.hour
    df["quadrante"]     = df.apply(
        lambda r: _get_quadrant(r["latitude"], r["longitude"]), axis=1
    )

    # ── Remove duplicatas ─────────────────────────────────────────────────────
    df.drop_duplicates(subset=["timestamp_unix"], inplace=True)

    # ── Padroniza nomes de colunas ────────────────────────────────────────────
    df.rename(columns={
        "timestamp_unix": "TIMESTAMP_UNIX",
        "timestamp_utc":  "TIMESTAMP_UTC",
        "latitude":       "LATITUDE",
        "longitude":      "LONGITUDE",
        "hora_utc":       "HORA_UTC",
        "quadrante":      "QUADRANTE",
        "message":        "MESSAGE",
        "ingestion_ts":   "INGESTION_TS",
        "source":         "SOURCE",
    }, inplace=True)

    return df


# ─── Transformação NEO ────────────────────────────────────────────────────────

def _transform_neo(data_dir: str) -> pd.DataFrame:
    """Lê todos os JSON brutos dos NEOs no diretório e retorna DataFrame limpo."""
    raw_files = sorted(glob.glob(os.path.join(data_dir, "neo_raw_*.json")))
    if not raw_files:
        raise FileNotFoundError(f"Nenhum arquivo neo_raw_*.json em {data_dir}")

    records = []
    for path in raw_files:
        with open(path, encoding="utf-8") as f:
            raw = json.load(f)

        ingestion_ts = raw.get("_ingestion_ts")

        for date_str, neos in raw.get("near_earth_objects", {}).items():
            for neo in neos:
                # Pega o dado de aproximação mais próximo
                approach = neo.get("close_approach_data", [{}])[0]
                miss_dist_km = approach.get("miss_distance", {}).get("kilometers")
                velocity_kms = approach.get("relative_velocity", {}).get(
                    "kilometers_per_second"
                )
                approach_date = approach.get("close_approach_date_full", date_str)

                # Diâmetro estimado (média entre mín e máx em km)
                diam = neo.get("estimated_diameter", {}).get("kilometers", {})
                diam_min = diam.get("estimated_diameter_min")
                diam_max = diam.get("estimated_diameter_max")
                diam_avg = (
                    (float(diam_min) + float(diam_max)) / 2
                    if diam_min and diam_max
                    else None
                )

                records.append({
                    "neo_id":          neo.get("id"),
                    "nome":            neo.get("name"),
                    "data_referencia": date_str,
                    "data_aproximacao": approach_date,
                    "diametro_km_avg": diam_avg,
                    "velocidade_kms":  velocity_kms,
                    "distancia_km":    miss_dist_km,
                    "is_perigoso":     neo.get("is_potentially_hazardous_asteroid", False),
                    "magnitude":       neo.get("absolute_magnitude_h"),
                    "ingestion_ts":    ingestion_ts,
                    "source":          "nasa_neows",
                })

    df = pd.DataFrame(records)

    # ── Limpeza ───────────────────────────────────────────────────────────────
    before = len(df)
    df.dropna(subset=["neo_id", "distancia_km", "velocidade_kms"], inplace=True)
    logger.info("NEO: %d -> %d registros (removidos: %d nulos)",
                before, len(df), before - len(df))

    # ── Conversão de tipos ────────────────────────────────────────────────────
    df["distancia_km"]   = pd.to_numeric(df["distancia_km"],   errors="coerce")
    df["velocidade_kms"] = pd.to_numeric(df["velocidade_kms"], errors="coerce")
    df["diametro_km_avg"] = pd.to_numeric(df["diametro_km_avg"], errors="coerce")
    df["magnitude"]      = pd.to_numeric(df["magnitude"],      errors="coerce")
    df["is_perigoso"]    = df["is_perigoso"].astype(bool)
    df["data_referencia"] = pd.to_datetime(df["data_referencia"], errors="coerce")

    # ── Remove duplicatas ─────────────────────────────────────────────────────
    df.drop_duplicates(subset=["neo_id", "data_referencia"], inplace=True)

    # ── Padroniza nomes de colunas ────────────────────────────────────────────
    df.rename(columns={
        "neo_id":           "NEO_ID",
        "nome":             "NOME",
        "data_referencia":  "DATA_REFERENCIA",
        "data_aproximacao": "DATA_APROXIMACAO",
        "diametro_km_avg":  "DIAMETRO_KM_AVG",
        "velocidade_kms":   "VELOCIDADE_KMS",
        "distancia_km":     "DISTANCIA_KM",
        "is_perigoso":      "IS_PERIGOSO",
        "magnitude":        "MAGNITUDE",
        "ingestion_ts":     "INGESTION_TS",
        "source":           "SOURCE",
    }, inplace=True)

    return df


# ─── Task principal ───────────────────────────────────────────────────────────

def transform_data(data_dir: str, **context) -> None:
    """
    Orquestra a transformação de ISS e NEO, salva CSVs limpos
    e empurra os caminhos via XCom.
    """
    logger.info("Iniciando transformacao | data_dir: %s", data_dir)

    # ISS
    df_iss = _transform_iss(data_dir)
    iss_path = os.path.join(data_dir, "iss_clean.csv")
    df_iss.to_csv(iss_path, index=False, encoding="utf-8")
    logger.info("ISS limpo salvo: %s (%d registros)", iss_path, len(df_iss))

    # NEO
    df_neo = _transform_neo(data_dir)
    neo_path = os.path.join(data_dir, "neo_clean.csv")
    df_neo.to_csv(neo_path, index=False, encoding="utf-8")
    logger.info("NEO limpo salvo: %s (%d registros)", neo_path, len(df_neo))

    context["ti"].xcom_push(key="iss_clean_path", value=iss_path)
    context["ti"].xcom_push(key="neo_clean_path", value=neo_path)
