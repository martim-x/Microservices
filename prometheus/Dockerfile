FROM alpine:3.19 AS builder
RUN apk add --no-cache gettext
RUN cp /usr/bin/envsubst /envsubst
RUN ldd /usr/bin/envsubst || true

FROM prom/prometheus:v3.11.3

COPY --from=builder /envsubst /bin/envsubst
COPY --from=builder /usr/lib/libintl.so.8 /usr/lib/libintl.so.8
COPY prometheus.yml /etc/prometheus/prometheus.yml.template

USER root

ENTRYPOINT []
CMD ["/bin/sh", "-c", "envsubst < /etc/prometheus/prometheus.yml.template > /etc/prometheus/prometheus.yml && /bin/prometheus --config.file=/etc/prometheus/prometheus.yml --storage.tsdb.path=/prometheus"]