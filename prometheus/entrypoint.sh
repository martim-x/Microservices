#!/bin/sh
set -eu

: "${AUTH_SERVICE_HOST:?AUTH_SERVICE_HOST is required}"
: "${AUTH_SERVICE_PORT:?AUTH_SERVICE_PORT is required}"
: "${ORDER_SERVICE_HOST:?ORDER_SERVICE_HOST is required}"
: "${ORDER_SERVICE_PORT:?ORDER_SERVICE_PORT is required}"
: "${USER_PRODUCT_SERVICE_HOST:?USER_PRODUCT_SERVICE_HOST is required}"
: "${USER_PRODUCT_SERVICE_PORT:?USER_PRODUCT_SERVICE_PORT is required}"
: "${REPORT_SERVICE_HOST:?REPORT_SERVICE_HOST is required}"
: "${REPORT_SERVICE_PORT:?REPORT_SERVICE_PORT is required}"

envsubst < /etc/prometheus/prometheus.yml.template > /etc/prometheus/prometheus.yml

echo "----- generated prometheus.yml -----"
cat /etc/prometheus/prometheus.yml
echo "-----------------------------------"

exec /bin/prometheus \
  --config.file=/etc/prometheus/prometheus.yml \
  --storage.tsdb.path=/prometheus