-- Consultas para el análisis de clientes de eCommerce (base: retail.sqlite)
-- Cada consulta empieza con "-- name: <nombre>" y termina en ";"
-- Fecha de referencia para recencia: 2011-12-10 (un día después de la última venta)

-- name: ingresos_mensuales
SELECT strftime('%Y-%m', fecha)                       AS mes,
       ROUND(SUM(ingreso), 2)                          AS ingresos,
       COUNT(DISTINCT factura)                         AS facturas,
       COUNT(DISTINCT cliente)                         AS clientes,
       ROUND(SUM(ingreso) / COUNT(DISTINCT factura), 2) AS ticket_promedio
FROM ventas
GROUP BY mes
ORDER BY mes;

-- name: ingresos_por_pais
SELECT pais,
       ROUND(SUM(ingreso), 2) AS ingresos,
       ROUND(100.0 * SUM(ingreso) / (SELECT SUM(ingreso) FROM ventas), 1) AS pct_total,
       COUNT(DISTINCT cliente) AS clientes
FROM ventas
GROUP BY pais
ORDER BY ingresos DESC
LIMIT 10;

-- name: top_productos
SELECT codigo, MAX(descripcion) AS producto,
       SUM(cantidad)           AS unidades,
       ROUND(SUM(ingreso), 2)  AS ingresos
FROM ventas
GROUP BY codigo
ORDER BY ingresos DESC
LIMIT 10;

-- name: tasa_devolucion
WITH v AS (SELECT strftime('%Y', fecha) AS anio, SUM(ingreso) AS ventas FROM ventas GROUP BY anio),
     d AS (SELECT strftime('%Y', fecha) AS anio, -SUM(ingreso) AS devuelto FROM devoluciones GROUP BY anio)
SELECT v.anio, ROUND(v.ventas, 2) AS ventas, ROUND(d.devuelto, 2) AS devuelto,
       ROUND(100.0 * d.devuelto / v.ventas, 1) AS pct_devuelto
FROM v JOIN d USING (anio)
ORDER BY v.anio;

-- name: nuevos_vs_recurrentes
WITH primera AS (
    SELECT cliente, MIN(strftime('%Y-%m', fecha)) AS mes_primera
    FROM ventas WHERE cliente IS NOT NULL GROUP BY cliente
)
SELECT strftime('%Y-%m', v.fecha) AS mes,
       COUNT(DISTINCT CASE WHEN strftime('%Y-%m', v.fecha) = p.mes_primera THEN v.cliente END) AS clientes_nuevos,
       COUNT(DISTINCT CASE WHEN strftime('%Y-%m', v.fecha) > p.mes_primera THEN v.cliente END) AS clientes_recurrentes
FROM ventas v JOIN primera p USING (cliente)
GROUP BY mes
ORDER BY mes;

-- name: rfm_clientes
WITH base AS (
    SELECT cliente,
           CAST(julianday('2011-12-10') - julianday(MAX(fecha)) AS INTEGER) AS recencia_dias,
           COUNT(DISTINCT factura)  AS frecuencia,
           ROUND(SUM(ingreso), 2)   AS monetario
    FROM ventas WHERE cliente IS NOT NULL
    GROUP BY cliente
),
puntajes AS (
    SELECT *,
           CASE WHEN recencia_dias <= 30 THEN 5 WHEN recencia_dias <= 90 THEN 4
                WHEN recencia_dias <= 180 THEN 3 WHEN recencia_dias <= 365 THEN 2 ELSE 1 END AS r,
           CASE WHEN frecuencia >= 9 THEN 5 WHEN frecuencia >= 5 THEN 4
                WHEN frecuencia >= 3 THEN 3 WHEN frecuencia = 2 THEN 2 ELSE 1 END AS f
    FROM base
)
SELECT cliente, recencia_dias, frecuencia, monetario, r, f,
       CASE WHEN r >= 4 AND f >= 4 THEN 'Campeones'
            WHEN r >= 3 AND f >= 3 THEN 'Leales'
            WHEN r >= 4 AND f <= 2 THEN 'Nuevos o prometedores'
            WHEN r <= 2 AND f >= 3 THEN 'En riesgo'
            WHEN r <= 2 AND f <= 2 THEN 'Inactivos'
            ELSE 'Necesitan atención' END AS segmento
FROM puntajes;

-- name: concentracion_clientes
WITH por_cliente AS (
    SELECT cliente, SUM(ingreso) AS ingreso FROM ventas WHERE cliente IS NOT NULL GROUP BY cliente
),
ordenado AS (
    SELECT ingreso,
           ROW_NUMBER() OVER (ORDER BY ingreso DESC) AS pos,
           COUNT(*) OVER () AS total
    FROM por_cliente
)
SELECT ROUND(100.0 * SUM(CASE WHEN pos <= total * 0.2 THEN ingreso END) / SUM(ingreso), 1) AS pct_ingreso_top20_clientes,
       COUNT(*) AS clientes
FROM ordenado;

-- name: cohortes_retencion
WITH primera AS (
    SELECT cliente, MIN(strftime('%Y-%m', fecha)) AS cohorte
    FROM ventas WHERE cliente IS NOT NULL GROUP BY cliente
),
actividad AS (
    SELECT DISTINCT v.cliente, p.cohorte, strftime('%Y-%m', v.fecha) AS mes
    FROM ventas v JOIN primera p USING (cliente)
),
tamanio AS (SELECT cohorte, COUNT(*) AS n FROM primera GROUP BY cohorte)
SELECT a.cohorte,
       (CAST(substr(a.mes, 1, 4) AS INTEGER) - CAST(substr(a.cohorte, 1, 4) AS INTEGER)) * 12
         + CAST(substr(a.mes, 6, 2) AS INTEGER) - CAST(substr(a.cohorte, 6, 2) AS INTEGER) AS mes_n,
       COUNT(*) AS clientes_activos,
       t.n AS tamano_cohorte,
       ROUND(100.0 * COUNT(*) / t.n, 1) AS retencion_pct
FROM actividad a JOIN tamanio t USING (cohorte)
GROUP BY a.cohorte, mes_n
ORDER BY a.cohorte, mes_n;

-- name: ingresos_por_cohorte
WITH primera AS (
    SELECT cliente, MIN(strftime('%Y-%m', fecha)) AS cohorte
    FROM ventas WHERE cliente IS NOT NULL GROUP BY cliente
)
SELECT p.cohorte,
       (CAST(substr(strftime('%Y-%m', v.fecha), 1, 4) AS INTEGER) - CAST(substr(p.cohorte, 1, 4) AS INTEGER)) * 12
         + CAST(substr(strftime('%Y-%m', v.fecha), 6, 2) AS INTEGER) - CAST(substr(p.cohorte, 6, 2) AS INTEGER) AS mes_n,
       ROUND(SUM(v.ingreso), 2) AS ingresos
FROM ventas v JOIN primera p USING (cliente)
GROUP BY p.cohorte, mes_n
ORDER BY p.cohorte, mes_n;
