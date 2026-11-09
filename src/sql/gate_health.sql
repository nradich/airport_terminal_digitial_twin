WITH worst AS (
  SELECT run_id, asset_id, prim_path, display_name, max(severity) AS severity,
    sum(CASE WHEN severity IS NULL THEN 1 ELSE 0 END) AS invalid_metrics
  FROM {{namespace}}.latest_state WHERE asset_type = 'gate'
  GROUP BY run_id, asset_id, prim_path, display_name
)
SELECT *, CASE WHEN invalid_metrics > 0 THEN NULL
  WHEN severity = 2 THEN 'crit' WHEN severity = 1 THEN 'warn' ELSE 'ok' END AS status,
  CASE WHEN invalid_metrics > 0 THEN NULL ELSE {{colour_expression}} END AS colour FROM worst
