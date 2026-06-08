-- ============================================================
-- queries_analiticas.sql
-- Disciplina: Big Data Architecture & Data Integration
-- FIAP Global Solution 2026 -- Industria Espacial
-- ============================================================

-- Q1: Distribuicao dos registros da ISS por hora do dia (UTC)
-- Mostra em quais horas do dia a ISS foi mais monitorada
SELECT
    HORA_UTC                        AS hora_utc,
    COUNT(*)                        AS total_registros,
    ROUND(AVG(LATITUDE),  4)        AS lat_media,
    ROUND(AVG(LONGITUDE), 4)        AS lon_media
FROM ISS_POSITIONS
GROUP BY HORA_UTC
ORDER BY HORA_UTC;

-- ============================================================

-- Q2: Top 10 NEOs mais proximos da Terra
-- Asteroides com menor distancia de aproximacao registrada
SELECT
    NEO_ID,
    NOME,
    ROUND(DISTANCIA_KM, 0)           AS distancia_km,
    ROUND(VELOCIDADE_KMS, 3)         AS velocidade_kms,
    ROUND(DIAMETRO_KM_AVG * 1000, 1) AS diametro_metros,
    CASE IS_PERIGOSO
        WHEN 1 THEN 'SIM'
        ELSE 'NAO'
    END                              AS potencialmente_perigoso,
    TO_CHAR(DATA_REFERENCIA, 'YYYY-MM-DD') AS data_referencia
FROM NEO_OBJECTS
ORDER BY DISTANCIA_KM ASC
FETCH FIRST 10 ROWS ONLY;

-- ============================================================

-- Q3: Distancia media, minima e maxima dos NEOs agrupada por mes
SELECT
    TO_CHAR(DATA_REFERENCIA, 'YYYY-MM')  AS mes_referencia,
    COUNT(*)                              AS total_neos,
    ROUND(AVG(DISTANCIA_KM), 0)           AS distancia_media_km,
    ROUND(MIN(DISTANCIA_KM), 0)           AS distancia_minima_km,
    ROUND(MAX(DISTANCIA_KM), 0)           AS distancia_maxima_km
FROM NEO_OBJECTS
GROUP BY TO_CHAR(DATA_REFERENCIA, 'YYYY-MM')
ORDER BY mes_referencia;

-- ============================================================

-- Q4: Distribuicao da ISS por quadrante geografico
-- Revela em qual regiao do planeta a ISS passa mais tempo
SELECT
    QUADRANTE,
    COUNT(*)                    AS total_registros,
    ROUND(MIN(LATITUDE),  4)    AS lat_minima,
    ROUND(MAX(LATITUDE),  4)    AS lat_maxima,
    ROUND(MIN(LONGITUDE), 4)    AS lon_minima,
    ROUND(MAX(LONGITUDE), 4)    AS lon_maxima
FROM ISS_POSITIONS
GROUP BY QUADRANTE
ORDER BY total_registros DESC;

-- ============================================================

-- Q5: Ranking dos NEOs potencialmente perigosos por velocidade
-- Usa funcao analitica RANK() OVER para ranquear por velocidade
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
ORDER BY VELOCIDADE_KMS DESC;
