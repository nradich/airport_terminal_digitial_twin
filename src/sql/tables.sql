CREATE TABLE IF NOT EXISTS {{namespace}}.assets (
  asset_id STRING, asset_type STRING, zone STRING, prim_path STRING, display_name STRING,
  asset_name STRING
) USING DELTA{{assets_location}};
CREATE TABLE IF NOT EXISTS {{namespace}}.flights (
  flight_id STRING, gate_id STRING, sched_dep TIMESTAMP, actual_dep TIMESTAMP,
  status STRING, run_id STRING
) USING DELTA{{flights_location}};
CREATE TABLE IF NOT EXISTS {{namespace}}.sensor_readings (
  asset_id STRING, ts TIMESTAMP, metric STRING, value_num DOUBLE, value_str STRING, run_id STRING
) USING DELTA{{sensor_readings_location}};
CREATE TABLE IF NOT EXISTS {{namespace}}.thresholds (
  asset_type STRING, metric STRING, warn DOUBLE, crit DOUBLE
) USING DELTA{{thresholds_location}};
CREATE TABLE IF NOT EXISTS {{namespace}}.scene_pushes (
  push_id STRING, ts TIMESTAMP, run_id STRING, n_prims INT, usd_path STRING,
  scenario STRING, step INT, preview_path STRING, capture_path STRING
) USING DELTA{{scene_pushes_location}};
