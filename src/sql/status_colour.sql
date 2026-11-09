CREATE OR REPLACE FUNCTION {{namespace}}.status_colour(value DOUBLE, warn DOUBLE, crit DOUBLE)
RETURNS STRING
RETURN CASE WHEN value IS NULL OR warn IS NULL OR crit IS NULL
  OR isnan(value) OR isnan(warn) OR isnan(crit)
  OR abs(value) = cast('Infinity' AS DOUBLE)
  OR abs(warn) = cast('Infinity' AS DOUBLE)
  OR abs(crit) = cast('Infinity' AS DOUBLE)
  OR warn >= crit THEN NULL
  WHEN value >= crit THEN '#EF4444'
  WHEN value >= warn THEN '#F59E0B'
  ELSE '#22C55E' END
