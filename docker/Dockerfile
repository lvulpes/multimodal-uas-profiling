# syntax=docker/dockerfile:1.7
#
# Build stages (use --target):
#   omnetpp  OMNeT++ core, headless
#   models   + INET + Simu5G
#   sim      + Gazebo, Python venv, capture tools   -> headless campaign runs, no Claude
#   claude   + Node, Claude Code, egress firewall, non-root user   -> default dev sandbox
#
# Pins: Simu5G v1.6.0 release notes say "tested with INET 4.5.4 and OMNeT++ 6.3, compatible with
# INET 4.6.0 and OMNeT++ 6.1-6.4". Re-check Simu5G's WHATSNEW.md before bumping anything.
#
# NOT YET BUILT/VERIFIED: download URL patterns and the INET/Simu5G build steps are written from the
# projects' documented procedure. Expect to adjust on the first build (the stages are split so a
# failure stays local and earlier layers stay cached).
#
# PX4 / ArduPilot SITL are intentionally not baked in; they are added in the POC once the flight
# stacks are chosen (built from pinned git submodules under sim/flight/).

ARG UBUNTU_VERSION=22.04

FROM ubuntu:${UBUNTU_VERSION} AS base
ENV DEBIAN_FRONTEND=noninteractive \
    TZ=Europe/Stockholm \
    LANG=C.UTF-8
SHELL ["/bin/bash", "-o", "pipefail", "-c"]
RUN apt-get update && apt-get install -y --no-install-recommends \
      ca-certificates curl git gnupg lsb-release \
      build-essential clang lld ccache make cmake pkg-config \
      bison flex perl \
      libxml2-dev zlib1g-dev libpcap-dev \
      python3 python3-dev python3-pip python3-venv \
    && rm -rf /var/lib/apt/lists/*

# ---------------------------------------------------------------- OMNeT++ (headless, no IDE/Qtenv)
FROM base AS omnetpp
ARG OMNETPP_VERSION=6.3.0
ARG OMNETPP_URL=https://github.com/omnetpp/omnetpp/releases/download/omnetpp-${OMNETPP_VERSION}/omnetpp-${OMNETPP_VERSION}-core.tgz
WORKDIR /opt
RUN curl -fsSL "${OMNETPP_URL}" | tar xz \
 && mv "omnetpp-${OMNETPP_VERSION}" omnetpp
WORKDIR /opt/omnetpp
RUN . ./setenv -q \
 && ./configure WITH_QTENV=no WITH_OSG=no WITH_OSGEARTH=no \
 && make -j"$(nproc)" MODE=release

# ---------------------------------------------------------------- INET + Simu5G
FROM omnetpp AS models
ARG INET_VERSION=4.5.4
ARG SIMU5G_REF=v1.6.0
ENV PATH=/opt/omnetpp/bin:${PATH} \
    LD_LIBRARY_PATH=/opt/omnetpp/lib
WORKDIR /opt
RUN curl -fsSL "https://github.com/inet-framework/inet/releases/download/v${INET_VERSION}/inet-${INET_VERSION}-src.tgz" | tar xz \
 && ln -s "$(ls -d inet4* | head -1)" inet
WORKDIR /opt/inet
RUN . /opt/omnetpp/setenv -q && . ./setenv -q \
 && make makefiles && make -j"$(nproc)" MODE=release

WORKDIR /opt
RUN git clone --depth 1 --branch "${SIMU5G_REF}" https://github.com/Unipisa/Simu5G.git simu5g
WORKDIR /opt/simu5g
# VERIFY: Simu5G expects INET as a sibling directory; the /opt/inet symlink is there for that.
RUN . /opt/omnetpp/setenv -q \
 && export INET_ROOT=/opt/inet \
 && . ./setenv -f \
 && make makefiles && make -j"$(nproc)" MODE=release

# ---------------------------------------------------------------- simulation toolchain
FROM base AS sim
ARG GZ_METAPACKAGE=gz-harmonic
RUN curl -fsSL https://packages.osrfoundation.org/gazebo.gpg -o /usr/share/keyrings/pkgs-osrf-archive-keyring.gpg \
 && echo "deb [arch=$(dpkg --print-architecture) signed-by=/usr/share/keyrings/pkgs-osrf-archive-keyring.gpg] http://packages.osrfoundation.org/gazebo/ubuntu-stable $(lsb_release -cs) main" \
      > /etc/apt/sources.list.d/gazebo-stable.list \
 && apt-get update && apt-get install -y --no-install-recommends \
      ${GZ_METAPACKAGE} \
      tcpdump tshark iproute2 iputils-ping jq less ripgrep gosu \
 && rm -rf /var/lib/apt/lists/*

COPY --from=models /opt /opt
COPY requirements.txt /tmp/requirements.txt
RUN python3 -m venv /opt/venv && /opt/venv/bin/pip install --no-cache-dir -r /tmp/requirements.txt

ENV OMNETPP_ROOT=/opt/omnetpp \
    INET_ROOT=/opt/inet \
    SIMU5G_ROOT=/opt/simu5g \
    PATH=/opt/venv/bin:/opt/omnetpp/bin:${PATH} \
    LD_LIBRARY_PATH=/opt/omnetpp/lib \
    PYTHONPATH=/workspace/src

# ---------------------------------------------------------------- Claude Code sandbox
FROM sim AS claude
ARG NODE_MAJOR=22
ARG CLAUDE_CODE_VERSION=latest
ARG USER_UID=1000
ARG USER_GID=1000

RUN apt-get update && apt-get install -y --no-install-recommends iptables ipset dnsutils \
 && curl -fsSL "https://deb.nodesource.com/setup_${NODE_MAJOR}.x" | bash - \
 && apt-get install -y --no-install-recommends nodejs \
 && rm -rf /var/lib/apt/lists/*
RUN npm install -g "@anthropic-ai/claude-code@${CLAUDE_CODE_VERSION}"

RUN groupadd -g "${USER_GID}" dev \
 && useradd -m -u "${USER_UID}" -g "${USER_GID}" -s /bin/bash dev \
 && mkdir -p /workspace /home/dev/.claude /home/dev/.ccache \
 && chown -R dev:dev /workspace /home/dev

COPY init-firewall.sh entrypoint.sh /usr/local/bin/
RUN chmod 0755 /usr/local/bin/init-firewall.sh /usr/local/bin/entrypoint.sh

ENV CLAUDE_CONFIG_DIR=/home/dev/.claude \
    CCACHE_DIR=/home/dev/.ccache
WORKDIR /workspace
# Starts as root only to install the firewall; entrypoint.sh then drops to user "dev" via gosu.
ENTRYPOINT ["/usr/local/bin/entrypoint.sh"]
CMD ["bash"]
