FROM ghcr.io/linuxserver/baseimage-ubuntu:jammy-version-dc27bfec

ENV PORT=8000

RUN echo "**** Installing build packages ****" && \
    apt update && apt upgrade -y && \
    apt install software-properties-common -y && \
    add-apt-repository ppa:deadsnakes/ppa -y && \
    apt install python3.11 python3-pip -y

# add local files
COPY /app /defaults/app
COPY /root /
COPY ./requirements.txt /tmp/


RUN echo "**** Installing required Python packages ****" && \
    python3.11 -m pip install -r /tmp/requirements.txt && \
    rm /tmp/requirements.txt
RUN echo "**** Fixing permission for s6 and server files ****" && \
    find /etc/s6-overlay/s6-rc.d/ -type f -exec chmod +x {} \; && \
    chmod +x /usr/bin/hketa-server

EXPOSE ${PORT}