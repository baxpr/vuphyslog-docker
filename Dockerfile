FROM python:2.7.16

# JDK for dcm4che
RUN apt-get update && apt-get install -y openjdk-8-jre zip

# dcm3che2
ENV DCM4CHE2 2.0.29
RUN cd /opt \
	&& wget -q https://sourceforge.net/projects/dcm4che/files/dcm4che2/${DCM4CHE2}/dcm4che-${DCM4CHE2}-bin.zip \
	&& unzip dcm4che-${DCM4CHE2}-bin.zip \
	&& rm -f dcm4che-${DCM4CHE2}-bin.zip

# dcm3che3
ENV DCM4CHE3 5.16.0
RUN cd /opt \
	&& wget -q https://sourceforge.net/projects/dcm4che/files/dcm4che3/${DCM4CHE3}/dcm4che-${DCM4CHE3}-bin.zip \
	&& unzip dcm4che-${DCM4CHE3}-bin.zip \
	&& rm -f dcm4che-${DCM4CHE3}-bin.zip

# Needed python modules
RUN pip install --upgrade pip \
	&& pip install pydicom pynetdicom

# Get the task-specific code
COPY . /app

# dcm3che paths
ENV PATH /opt/dcm4che-${DCM4CHE2}/bin:/opt/dcm4che-${DCM4CHE3}/bin:$PATH
