FROM prom/prometheus

COPY prometheus.yml /etc/prometheus/prometheus.yml.template

USER root
RUN apk add --no-cache gettext

CMD sh -c "envsubst < /etc/prometheus/prometheus.yml.template > /etc/prometheus/prometheus.yml && \
    /bin/prometheus \
    --config.file=/etc/prometheus/prometheus.yml \
    --storage.tsdb.path=/prometheus"