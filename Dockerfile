FROM ghcr.io/linuxserver/baseimage-ubuntu:jammy-version-dc27bfec

ENV PORT=8000

RUN apt update && apt upgrade -y && \
    apt install software-properties-common -y && \
    add-apt-repository ppa:deadsnakes/ppa -y && \
    apt install python3.11 python3-pip -y

# add local files
COPY /app /defaults/app
COPY /requirements.txt /defaults/app/
COPY /root /

EXPOSE ${PORT}