NextGIS Web Docker Environment
==============================

## Requirements

* Docker CE >= 17.06
* Docker Compose >= 1.14
* Package python-mako (provides `mako-render` command)

## Installation

Check that Docker installed and configured correctly:

    $ docker run hello-world
    Hello from Docker!
    This message shows that your installation appears to be working correctly.
    ...(snipped)...

Clone this repository:

    $ git clone git@github.com:nextgis/ngwdocker.git
    $ cd ngwdocker

Clone or copy `nextgisweb` to `package/` directory:

    $ git clone git@github.com:nextgis/nextgisweb.git package/nextgisweb

Clone or copy other `nextgisweb_*` packages to same directory. For example `nextgisweb_mapserver` and `nextgisweb_qgis`:

    $ git clone git@github.com:nextgis/nextgisweb_mapserver.git package/nextgisweb_mapserver
    $ git clone git@github.com:nextgis/nextgisweb_qgis.git package/nextgisweb_qgis

Keep in mind that symlinks doesn't work here due to Docker limitations. You can use [BindFS](http://bindfs.org/) as alternative to symlinks.

Generate dockerfile from mako template and run Docker Compose:

    $ mako-render Dockerfile.mako > Dockerfile
    $ docker-compose build
    $ docker-compose create

Build python *.egginfo files for `nextgisweb_*` packages:

    $ docker-compose run shell /src/util/egginfo

Initialize database structure:

    $ docker-compose run shell /src/util/initdb

## Usage

Start pserve service and go to http://localhost:20080:

    $ docker-compose start pserve
    $ browse http://localhost:20080
