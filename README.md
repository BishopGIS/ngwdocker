NextGIS Web Docker Environment
==============================

## Requirements

* Docker CE >= 17.06
* Docker Compose >= 1.14
* Python 3 with:
    * YAML library (`python3-yaml` package in Ubuntu)
    * Click library (`python3-click` package in Ubuntu)

## Installation

Check that Docker installed and configured correctly:

    $ docker run hello-world
    Hello from Docker!
    ...(snipped)...

Clone this repository:

    $ git clone git@github.com:nextgis/ngwdocker.git
    $ cd ngwdocker

Clone or copy `nextgisweb` to `package/` directory:

    $ git clone git@github.com:nextgis/nextgisweb.git package/nextgisweb

Clone or copy other `nextgisweb_*` packages to same directory. For example `nextgisweb_mapserver` and `nextgisweb_qgis`:

    $ git clone git@github.com:nextgis/nextgisweb_mapserver.git package/nextgisweb_mapserver
    $ git clone git@github.com:nextgis/nextgisweb_qgis.git package/nextgisweb_qgis

Generate `Dockerfile` and `docker-compose.yaml`:

    $ python3 ngwdocker.py

Start postgres and initialize database structure:

    $ docker-compose up -d postgres
    # Wait 5-10 seconds for PostgreSQL start
    $ docker-compose run app nextgisweb initialize_db

Start webserver:

    $ docker-compose up app

Go to http://localhost:8080 in browser.

## Development mode

By default package sources from `package/*` directory are copied to image and each change in sources requires image rebuild with `docker-compose build app`.

In development mode package sources mounted to container via volume. To use development mode add option to `ngwdocker.py`:

    $ python3 ngwdocker.py --development
    $ docker-compose up ...

**NOTE:** To avoid problems with file ownership and permissions image build with current users UID and GID (1000 for firstly created user on Ubuntu desktop).

But some changes still requires image rebuild:

* Requirements changes in `setup.py`
* Entrypoint changes in `setup.py`
