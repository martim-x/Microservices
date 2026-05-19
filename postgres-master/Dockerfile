FROM postgres:18.3

ENV TZ=Europe/Minsk
ENV PGTZ=Europe/Minsk

CMD ["postgres", "-c", "wal_level=logical", "-c", "max_wal_senders=10", "-c", "max_replication_slots=10"]