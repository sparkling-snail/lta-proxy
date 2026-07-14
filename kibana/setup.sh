#!/bin/bash
# Waits for Kibana to be ready, then creates the lta-proxy data view automatically.

KIBANA_URL="http://kibana:5601"
MAX_WAIT=120
WAITED=0

echo "Waiting for Kibana to be ready..."
until curl -s "$KIBANA_URL/api/status" | grep -q '"level":"available"'; do
  sleep 5
  WAITED=$((WAITED + 5))
  if [ $WAITED -ge $MAX_WAIT ]; then
    echo "Kibana did not become ready in time. Exiting."
    exit 1
  fi
  echo "Still waiting... (${WAITED}s)"
done

echo "Kibana is ready. Creating data view..."

curl -s -X POST "$KIBANA_URL/api/data_views/data_view" \
  -H "Content-Type: application/json" \
  -H "kbn-xsrf: true" \
  -d '{
    "data_view": {
      "title": "lta-proxy-*",
      "name": "LTA Proxy Logs",
      "timeFieldName": "@timestamp"
    }
  }'

echo ""
echo "Data view created. Open Kibana → Discover to see your logs."
