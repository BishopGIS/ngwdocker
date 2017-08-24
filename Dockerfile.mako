<%
import os, os.path, collections
packages = sorted(filter(lambda p: os.path.isdir(os.path.join('package', p)), os.listdir('package')))
pdict = collections.OrderedDict()
prepfiles = []
debpackages = ['git', 'mc', 'build-essential', 'python-dev', 'python-virtualenv']
for p in packages:
    obj = collections.OrderedDict()
    pdict[p] = obj
    dpath = os.path.join('.', 'package', p, 'docker')
    if not os.path.isdir(dpath):
        continue
    obj['source_path'] = dpath
    obj['build_path'] = os.path.join('build', p)
    obj['requirements'] = os.path.isfile(os.path.join(dpath, 'requirements'))
    obj['envsetup'] = os.path.isfile(os.path.join(dpath, 'envsetup.dockerfile'))

    pdfile = os.path.join(dpath, 'prepeare.dockerfile')
    if os.path.isfile(pdfile):
        with open(pdfile, 'r') as fd:
            prepfiles.append('# Package ' + p)
            prepfiles.append(fd.read())

    dpfile = os.path.join(dpath, 'debpackages')
    if os.path.isfile(dpfile):
        with open(dpfile, 'r') as fd:
            debpackages.append(fd.read())
%>

FROM ubuntu:16.04
RUN mkdir /build /src /src/package

${'\n'.join(prepfiles)}

# Update repositories & install packages
RUN apt-get update && apt-get install -y  ${' '.join(debpackages)}

# Setup virtualenv
RUN /usr/bin/virtualenv /env && /env/bin/pip install --upgrade pip

%for package, pdef in pdict.iteritems():
# Package ${package}
ADD ${pdef['source_path']} ${pdef['build_path']}
%if pdef['requirements']:
RUN /env/bin/pip install -r ${pdef['build_path']}/requirements
%endif
%if pdef['envsetup']:
<% with open(os.path.join(pdef['source_path'], 'envsetup.dockerfile'), 'r') as fd: inccont = fd.read() %>${inccont}
%endif

%endfor

ADD ./package /src/package

%for package in packages:
RUN echo ${package} >> /build/package
RUN /env/bin/pip install -e /src/package/${package}
%endfor