WITH ranked AS (
  SELECT *, row_number() OVER (
    PARTITION BY run_id, asset_id, metric{{time_partition}} ORDER BY ts DESC
  ) AS rn FROM {{readings}}
), scored AS (
  SELECT r.asset_id, r.run_id, r.ts, r.metric, r.value_num, r.value_str,
    a.asset_type, a.prim_path, a.display_name, t.warn, t.crit,
    CASE
      WHEN r.metric = 'jet_bridge_status' THEN CASE
        WHEN value_str = 'fault' THEN 2 WHEN value_str IN ('docked','idle') THEN 0 END
      WHEN r.metric = 'flight_status' THEN CASE
        WHEN value_str = 'delayed' THEN 1
        WHEN value_str IN ('on_time','boarding','departed') THEN 0 END
      WHEN r.value_num IS NULL OR isnan(r.value_num) OR abs(r.value_num) = cast('Infinity' AS DOUBLE)
        OR t.warn IS NULL OR t.crit IS NULL OR t.warn >= t.crit THEN NULL
      WHEN r.value_num >= t.crit THEN 2 WHEN r.value_num >= t.warn THEN 1 ELSE 0
    END AS severity
  FROM ranked r JOIN {{assets_source}} a ON r.asset_id = a.asset_id
  LEFT JOIN {{thresholds_source}} t ON a.asset_type = t.asset_type AND r.metric = t.metric
  WHERE rn = 1
)
SELECT *, CASE severity WHEN 2 THEN 'crit' WHEN 1 THEN 'warn' WHEN 0 THEN 'ok' END AS status,
  {{colour_expression}} AS colour FROM scored
