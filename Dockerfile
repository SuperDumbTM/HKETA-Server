FROM python:3.11.5-alpine3.18

ARG S6_OVERLAY_VERSION="3.1.5.0"
ARG S6_OVERLAY_ARCH="x86_64"

ENV PORT=8000
ENV PYTHONUNBUFFERED=1
ENV PS1="$(whoami)@$(hostname):$(pwd)\\$ " \
  HOME="/root" \
  TERM="xterm" \
  S6_VERBOSITY=1

# add s6 overlay
ADD https://github.com/just-containers/s6-overlay/releases/download/v${S6_OVERLAY_VERSION}/s6-overlay-noarch.tar.xz /tmp
RUN tar -C / -Jxpf /tmp/s6-overlay-noarch.tar.xz
ADD https://github.com/just-containers/s6-overlay/releases/download/v${S6_OVERLAY_VERSION}/s6-overlay-${S6_OVERLAY_ARCH}.tar.xz /tmp
RUN tar -C / -Jxpf /tmp/s6-overlay-${S6_OVERLAY_ARCH}.tar.xz

RUN \
  echo "**** Installing runtime packages ****" && \
  apk add --no-cache \
    bash \
    xz \
    bash \
    ca-certificates \
    coreutils \
    curl \
    jq \
    procps-ng \
    shadow \
    tzdata

# add local files
COPY /app /defaults/app
COPY /root /
COPY ./requirements.txt /tmp/

# create user
RUN echo "**** Creating abc user****" && \
    groupmod -g 1000 users && \
    useradd -u 911 -U -d /config -s /bin/false abc && \
    usermod -G users abc
# install python dependencies
RUN echo "**** Installing required Python packages ****" && \
    python3 -m pip install -r /tmp/requirements.txt
# fix s6 files permission
RUN echo "**** Fixing permission for s6 and service files ****" && \
    find /etc/s6-overlay/s6-rc.d/ -type f -exec chmod +x {} \; && \
    chmod +x /usr/bin/hketa-server /usr/bin/cont-chown
# cleanup
RUN echo "**** cleanup ****" && \
    rm -rfv /tmp/*

EXPOSE ${PORT}

ENTRYPOINT [ "/init" ]