#!/usr/bin/env bash
# Stops the Prometheus container and removes the generated data. Run with: ./teardown.sh
cd "$(dirname "$0")" || exit 1
docker rm -f promql-gym >/dev/null 2>&1 && echo "removed the container promql-gym"
docker run --rm --user 0:0 -v "$PWD:/w" --entrypoint sh prom/prometheus:v2.55.1 -c 'rm -rf /w/data /w/gym/incident.om' >/dev/null 2>&1
rm -rf data gym/incident.om
echo "Now run ./verify-teardown.sh"
