FROM python:2.7.16-slim-stretch

# Hack to deal with jre dependencies/install bug
RUN mkdir -p /usr/share/man/man1

# JDK for dcm4che
RUN apt-get update && \
	apt-get install -y --no-install-recommends \
	openjdk-8-jre-headless \
	zip unzip wget

# dcm3che2
ENV DCM4CHE2 2.0.29
RUN cd /opt \
	&& wget -q https://sourceforge.net/projects/dcm4che/files/dcm4che2/${DCM4CHE2}/dcm4che-${DCM4CHE2}-bin.zip \
	&& unzip dcm4che-${DCM4CHE2}-bin.zip \
	&& rm -f dcm4che-${DCM4CHE2}-bin.zip

# Get the task-specific code
COPY . /app

# Needed python modules
RUN pip install -r /app/requirements.txt

# dcm3che paths
ENV PATH /opt/dcm4che-${DCM4CHE2}/bin:$PATH
