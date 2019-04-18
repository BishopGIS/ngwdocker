#!/bin/sh
set -e
. /opt/ngw/env/bin/activate

if [ "$NGWDOCKER_MODE" = "development" ]; then
    for pkg in $NGWDOCKER_PACKAGES; do
        if [ ! -d "/opt/ngw/package/$pkg/$pkg.egg-info" ]; then
            pip install --no-deps -e /opt/ngw/package/$pkg
        fi
    done
fi

until nextgisweb initialize_db
do
    echo "Can't initialize yet. Waiting for database ready?"
    sleep 1
done

exec "$@"
