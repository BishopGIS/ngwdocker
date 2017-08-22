<%
import os, os.path, collections
packages = sorted(filter(lambda p: os.path.isdir(os.path.join('package', p)), os.listdir('package')))
pdict = collections.OrderedDict()
for p in packages:
    obj = collections.OrderedDict()
    pdict[p] = obj
    dpath = os.path.join('.', 'package', p, 'docker')
    if not os.path.isdir(dpath):
        continue
    obj['source_path'] = dpath
    obj['build_path'] = os.path.join('build', p)
    obj['requirements'] = os.path.isfile(os.path.join(dpath, 'requirements'))
    obj['envsetup'] = os.path.isfile(os.path.join(dpath, 'include'))
%>

FROM ubuntu:16.04

RUN apt-get update && apt-get install -y \
    git mc build-essential python-dev python-virtualenv \
    libgdal-dev g++ libxml2-dev libxslt1-dev gdal-bin libgeos-dev zlib1g-dev libjpeg-turbo8-dev

RUN /usr/bin/virtualenv /env && /env/bin/pip install --upgrade pip

RUN mkdir /build

%for package, pdef in pdict.iteritems():
# ${package}
ADD ${pdef['source_path']} ${pdef['build_path']}
%if pdef['requirements']:
RUN /env/bin/pip install -r ${pdef['build_path']}/requirements
%endif
%if pdef['envsetup']:
<% with open(os.path.join(pdef['source_path'], 'include'), 'r') as fd: inccont = fd.read() %>${inccont}
%endif

%endfor

RUN mkdir --parents /src/package && touch /build/package
ADD ./package /src/package

%for package in packages:
RUN echo ${package} >> /build/package
RUN /env/bin/pip install -e /src/package/${package}
%endfor