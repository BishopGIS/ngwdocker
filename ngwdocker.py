import sys
import importlib.util
from collections import OrderedDict
from io import StringIO
import os
import os.path
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

    def requirements(self):
        fn = os.path.join('package', self.name, 'docker', 'requirements')
        if os.path.isfile(fn):
            return fn

    def envsetup(self):
        pass


def load_packages():
    pkgnames = sorted(filter(
        lambda p: os.path.isdir(os.path.join('package', p)),
        os.listdir('package')))

    packages = OrderedDict()
    for p in pkgnames:
        spec = importlib.util.spec_from_file_location(
            '{}.docker'.format(p),
            os.path.join('package', p, 'docker.py'))
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        packages[p] = module.Package(p)
    return packages


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
        "RUN /usr/bin/virtualenv /opt/ngw/env")

    for p in packages.values():
        dockerfile.write('\n# {}\n'.format(p.name))

        locfn = p.requirements()
        if locfn is not None:
            imgfn = os.path.join('/opt/ngw/build', p.name + "-requirements")
            dockerfile.write(
                'COPY {} {}'.format(locfn, imgfn),
                'RUN /opt/ngw/env/bin/pip install -r {}'.format(imgfn))

        p.envsetup()

    dockerfile.write("\n# NEXTGISWEB PACKAGES", "")

    for p in packages.values():
        if mode == Mode.PRODUCTION:
            dockerfile.write('COPY --chown=ngw:ngw package/{pkg} /opt/ngw/package/{pkg}'.format(pkg=p.name))
            dockerfile.write('RUN /opt/ngw/env/bin/pip install -e /opt/ngw/package/{pkg}'.format(pkg=p.name))
        else:
            dockerfile.write('COPY --chown=ngw:ngw package/{pkg}/setup.py /opt/ngw/package/{pkg}/setup.py'.format(pkg=p.name))
            dockerfile.write('RUN /opt/ngw/env/bin/pip install -e /opt/ngw/package/{pkg}'.format(pkg=p.name))

    dockerfile.write("\n# FINALIZE\n")

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
    dcomp['services'] = svc = OrderedDict()
    dcomp['volumes'] = vlm = OrderedDict()

    srcvol = ["./package:/opt/ngw/package"] if mode == Mode.DEVELOPMENT else []
    bargs = OrderedDict(uid=os.getuid(), gid=os.getgid()) if mode == Mode.DEVELOPMENT else {}

    svc['app'] = OrderedDict(
        build=OrderedDict(context=".", args=bargs),
        command="pserve-development",
        depends_on=['postgres'],
        volumes=['data:/opt/ngw/data'] + srcvol,
        ports=['8080:8080'],
    )
    vlm['data'] = OrderedDict()

    svc['postgres'] = OrderedDict(
        build=OrderedDict(context='./postgres'),
        environment=OrderedDict(POSTGRES_USER='ngw')
    )

    if ctx.params['minio']:
        svc['minio'] = OrderedDict(
            image='minio/minio',
        )

    def dict_representer(dumper, data):
        return dumper.represent_dict(data.items())

    yaml.add_representer(OrderedDict, dict_representer)

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
