import sys

python3 = True
try:
    import importlib.util
except ImportError:
    python3 = False
    import imp

from collections import OrderedDict
if python3:
    from io import StringIO
else:
    from io import BytesIO as StringIO
import os
import os.path
from datetime import datetime
import random
import string
from enum import Enum
import yaml
import click


class Mode(Enum):
    PRODUCTION = 'production'
    DEVELOPMENT = 'development'


class Dockerfile:

    def __init__(self):
        self.buf = StringIO()

    def write(self, *lines):
        self.buf.write("\n".join(lines) + "\n")


class PackageBase:

    def __init__(self, name):
        self.name = name

    def options(self, func):
        return func

    def debpackages(self):
        return ()

    def envsetup(self):
        pass

def load_module(module_name, filename):
    try:
        if python3:
            spec = importlib.util.spec_from_file_location(module_name, filename)
            module = importlib.util.module_from_spec(spec)
            spec.loader.exec_module(module)
            return module
        else:
            module = imp.load_source(module_name.split('.')[-1], filename)
            return module
    except:
        return None

def load_packages():
    pkgnames = sorted(filter(
        lambda p: os.path.isdir(os.path.join('package', p)),
        os.listdir('package')))

    packages = OrderedDict()
    for p in pkgnames:
        module = load_module(
            '{}.docker'.format(p),
            os.path.join('package', p, 'docker.py')
        )
        if module is not None:
            packages[p] = module.Package(p)
    return packages


def read_envfile(fn='.env'):
    result = dict()
    if os.path.isfile(fn):
        with open(fn, 'r') as fp:
            for l in fp:
                var, val = l.rstrip('\n').split('=', 1)
                result[var] = val
    return result


def write_envfile(values, fn='.env'):
    # Keep original file backup on content changes
    original = read_envfile(fn)
    if original != values and original != dict():
        suffix = datetime.now().replace(microsecond=0).isoformat() \
            .replace(':', '').replace('-', '').replace('T', '-')
        os.rename(fn, fn + '-' + suffix)

    # Write new file contents
    with open(fn, 'w') as fd:
        for k, v in values.items():
            fd.write('{}={}\n'.format(k, v))


def pwgen(length=16):
    return ''.join(random.SystemRandom().choice(
        string.ascii_letters + string.digits) for _ in range(16))


def main(packages, ctx, mode, **kwargs):
    dockerfile = Dockerfile()
    for p in packages.values():
        p.dockerfile = dockerfile

    dockerfile.write(
        "FROM ubuntu:18.04", "",
        "ENV LC_ALL=C.UTF-8",
        "")

    dockerfile.write("# DEBPACKAGES", "")

    debpackages = [
        ('common', (
            'git', 'mc', 'build-essential', 'python-dev',
            'virtualenv', 'python-virtualenv'))]

    for p in packages.values():
        pkgs = p.debpackages()
        if len(pkgs) > 0:
            debpackages.append((p.name, p.debpackages()))

    line = "RUN apt-get update && \\\n" \
           "    DEBIAN_FRONTEND=noninteractive apt-get install -y --no-install-recommends \\\n"

    line += " \\\n".join(map(lambda i: '        ' + ' '.join(i[1]), debpackages))
    line += " && \\\n    rm -rf /var/lib/apt/lists/*"

    dockerfile.write(line, "")

    dockerfile.write(
        " # SETUP NGW USER", "",
        "ARG uid=1000",
        "ARG gid=1000",
        "RUN groupadd -g $gid ngw && useradd --home /opt/ngw -u $uid -g $gid ngw",
        "RUN mkdir -p /opt/ngw/build /opt/ngw/package /opt/ngw/data",
        "RUN chown -R ngw:ngw /opt/ngw",
        "WORKDIR /opt/ngw",
        "USER ngw",
        "")

    dockerfile.write(
        "# VIRTUALENV", "",
        "RUN /usr/bin/virtualenv /opt/ngw/env",
        "RUN /opt/ngw/env/bin/pip install --no-cache-dir uwsgi")

    for p in packages.values():
        dockerfile.write('\n# {}\n'.format(p.name))
        p.envsetup()

    dockerfile.write("\n# NEXTGISWEB PACKAGES", "")

    for p in packages.values():
        if mode == Mode.PRODUCTION:
            dockerfile.write(
                "COPY --chown=ngw:ngw package/{pkg} /opt/ngw/package/{pkg}".format(pkg=p.name),
                "RUN /opt/ngw/env/bin/pip install --no-cache-dir -e /opt/ngw/package/{pkg}".format(pkg=p.name))
        else:
            # Copy only setup.py for requirements and entrypoints installation
            dockerfile.write(
                "COPY --chown=ngw:ngw package/{pkg}/setup.py /opt/ngw/package/{pkg}/setup.py".format(pkg=p.name),
                "RUN /opt/ngw/env/bin/pip install --no-cache-dir -e /opt/ngw/package/{pkg}".format(pkg=p.name))

        dockerfile.write("")

    if mode == Mode.PRODUCTION:
        dockerfile.write(
            "RUN /opt/ngw/env/bin/nextgisweb-i18n compile",
            "")

    dockerfile.write("# FINALIZE", "")

    dockerfile.write(
        "COPY docker-entrypoint.sh /",
        "COPY --chown=ngw:ngw bin /opt/ngw/env/bin",
        "COPY --chown=ngw:ngw config /opt/ngw/config",
        "")

    dockerfile.write('ENTRYPOINT ["/docker-entrypoint.sh"]', '')

    dockerfile.write(
        'ENV NGWDOCKER_MODE {}'.format(mode.value),
        'ENV NGWDOCKER_PACKAGES {}'.format(" ".join(packages.keys())),
        'ENV NEXTGISWEB_CONFIG /opt/ngw/config/config.ini',
        'ENV NEXTGISWEB_LOGGING /opt/ngw/config/logging.ini',
        "")

    with open('Dockerfile', 'w') as fd:
        fd.write(dockerfile.buf.getvalue())

    dcomp = OrderedDict(version="3.2")
    envfile = read_envfile()

    dcomp['services'] = svc = OrderedDict()
    dcomp['volumes'] = vlm = OrderedDict()

    # Service: app

    srcvol = ["./package:/opt/ngw/package"] if mode == Mode.DEVELOPMENT else []
    bargs = OrderedDict(uid=os.getuid(), gid=os.getgid()) \
        if mode == Mode.DEVELOPMENT else {}

    if 'SESSION_SECRET' not in envfile:
        envfile['SESSION_SECRET'] = pwgen()

    if 'DATABASE_PASSWORD' not in envfile:
        envfile['DATABASE_PASSWORD'] = pwgen()

    svc['app'] = OrderedDict(
        build=OrderedDict(context=".", args=bargs),
        command="pserve-development" if mode == Mode.DEVELOPMENT else 'uwsgi-production',
        environment=OrderedDict(
            NEXTGISWEB_CORE_DATABASE_PASSWORD="${DATABASE_PASSWORD}",
            NEXTGISWEB_PYRAMID_SECRET="${SESSION_SECRET}",
            NEXTGISWEB_DEFAULT_LOCALE="ru"),
        depends_on=['postgres'],
        volumes=['data:/opt/ngw/data'] + srcvol,
        ports=['8080:8080'],
    )
    vlm['data'] = OrderedDict()

    svc['postgres'] = OrderedDict(
        build=OrderedDict(context='./postgres'),
        environment=OrderedDict(POSTGRES_PASSWORD="${DATABASE_PASSWORD}"),
        volumes=['postgres:/var/lib/postgresql/data']
    )
    vlm['postgres'] = OrderedDict()

    if ctx.params['minio']:
        svc['minio'] = OrderedDict(
            image='minio/minio',
        )

    def dict_representer(dumper, data):
        return dumper.represent_dict(data.items())

    yaml.add_representer(OrderedDict, dict_representer)

    write_envfile(envfile)

    with open('docker-compose.yaml', 'w') as fd:
        yaml.dump(dcomp, fd, default_flow_style=False)


if __name__ == '__main__':
    packages = load_packages()

    def package_options(func):
        for p in packages.values():
            func = p.options(func)
        return func

    @click.command()
    @click.option('--production', 'mode', flag_value=Mode.PRODUCTION, default=True, help="Build production environment.")
    @click.option('--development', 'mode', flag_value=Mode.DEVELOPMENT, help="Build development environment.")
    @click.option('--minio', flag_value=True, help="Add minio docker service to compose file.")
    @package_options
    @click.pass_context
    def cmd(ctx, **kwargs):
        main(packages, ctx, **kwargs)

    cmd()
