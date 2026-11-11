#!/usr/bin/env bash
# Generates the recorded night, loads it into a Prometheus and starts it on http://localhost:9099. Run: ./setup.sh
set -u
cd "$(dirname "$0")"
for c in docker python3; do command -v "$c" >/dev/null || { echo "MISSING: $c"; exit 1; }; done
docker info >/dev/null 2>&1 || { echo "Docker is not running."; exit 1; }
if docker ps -a --filter name=promql-gym -q | grep -q .; then echo "The gym is already set up. Run ./teardown.sh first to start over."; exit 1; fi
if (exec 3<>/dev/tcp/127.0.0.1/9099) 2>/dev/null; then echo "Port 9099 is in use on your machine."; exit 1; fi
echo "Generating six hours of metrics..."
python3 gym/gen_incident.py gym/incident.om || exit 1
rm -rf data && mkdir -p data
echo "Loading them into a Prometheus time-series database (promtool backfill)..."
docker run --rm --user 0:0 -v "$PWD/gym:/in:ro" -v "$PWD/data:/data" --entrypoint promtool prom/prometheus:v2.55.1 tsdb create-blocks-from openmetrics /in/incident.om /data >/tmp/promql-gym-backfill.log 2>&1 || { cat /tmp/promql-gym-backfill.log; echo "backfill failed"; exit 1; }
docker run -d --name promql-gym --user 0:0 -p 127.0.0.1:9099:9090 -v "$PWD/data:/prometheus" prom/prometheus:v2.55.1 \
  --config.file=/etc/prometheus/prometheus.yml --storage.tsdb.path=/prometheus --storage.tsdb.retention.time=36500d >/dev/null || { echo "could not start Prometheus"; exit 1; }
for _ in $(seq 1 40); do curl -fs http://127.0.0.1:9099/-/ready >/dev/null 2>&1 && break; sleep 1; done
cat <<TXT

Prometheus is ready: http://localhost:9099
The recorded night starts at 2026-01-01 00:00:00 UTC (unix time 1767225600) and lasts six hours.
Each question in queries.yaml says at which moment of the night it is asked (the "time" field, in hours:minutes after the start).
In the Prometheus UI, use the "Evaluation time" box (Graph tab > Table) to ask a question at that moment, for example 2026-01-01 03:15:00.
TXT
