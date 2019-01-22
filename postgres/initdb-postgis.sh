#!/bin/sh
set -e

# Perform all actions as $POSTGRES_USER
export PGUSER="$POSTGRES_USER"

"${psql[@]}" --dbname="$DB" <<-'EOSQL'
    CREATE EXTENSION IF NOT EXISTS postgis;
    CREATE EXTENSION IF NOT EXISTS hstore;
EOSQL
