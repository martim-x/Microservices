FROM prom/prometheus:v3.11.3 AS prom

FROM alpine:3.19

RUN apk add --no-cache gettext

COPY --from=prom /bin/prometheus /bin/prometheus
COPY prometheus.yml.template /etc/prometheus/prometheus.yml.template
COPY entrypoint.sh /entrypoint.sh

RUN chmod +x /entrypoint.sh \
    && mkdir -p /prometheus /etc/prometheus

EXPOSE 9090

ENTRYPOINT ["/entrypoint.sh"]