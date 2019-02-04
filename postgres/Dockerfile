FROM mdillon/postgis:10

# Owerwrite original postgis initialization script
COPY ./initdb-postgis.sh /docker-entrypoint-initdb.d/postgis.sh

ENV POSTGRES_USER nextgisweb
