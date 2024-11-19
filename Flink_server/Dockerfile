FROM flink:1.18.1-java11
# install python3 and pip3
RUN apt-get update -y && \
apt-get install -y openjdk-11-jdk python3 python3-pip python3-dev gdebi-core sudo awscli
RUN ln -s /usr/bin/python3 /usr/bin/python
COPY requirements.txt /
ENV JAVA_HOME /usr/lib/jvm/java-11-openjdk-arm64
RUN pip3 install -r /requirements.txt


