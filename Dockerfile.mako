<%
import os, os.path
packages = sorted(filter(os.path.isdir, os.listdir('package')))
%>

FROM ubuntu:16.04

RUN apt-get update && apt-get install -y \
    git mc build-essential python-dev python-virtualenv \
    libgdal-dev g++ libxml2-dev libxslt1-dev gdal-bin libgeos-dev zlib1g-dev libjpeg-turbo8-dev

RUN /usr/bin/virtualenv /env && /env/bin/pip install --upgrade pip

RUN mkdir /build

%for package in packages:
%if os.path.isdir('package/' + package + '/docker'):
ADD ./package/${package}/docker /build/${package}
%endif
%if os.path.isfile('package/' + package + '/docker/requirements'):
RUN /env/bin/pip install -r /build/${package}/requirements
%endif
<% incfile = os.path.join('package', package, 'docker/include') %>
%if os.path.isfile(incfile):
<% with open(incfile, 'r') as fd: inccont = fd.read() %>${inccont}
%endif
%endfor

RUN mkdir --parents /src/package
ADD ./package /src/package

%for package in packages:
RUN /env/bin/pip install -e /src/package/${package}
%endfor