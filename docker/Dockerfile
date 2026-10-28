# syntax=docker/dockerfile:1.7
#
# Build stages (use --target):
#   omnetpp  OMNeT++ core, headless
#   models   + INET + Simu5G
#   sim      + Gazebo, Python venv, capture tools   -> headless campaign runs, no Claude
#   flight   + PX4 SITL and ArduPilot SITL, built at pinned tags
#   claude   + Node, Claude Code, egress firewall, non-root user   -> default dev sandbox
#
# Pins: Simu5G v1.6.0 release notes say "tested with INET 4.5.4 and OMNeT++ 6.3, compatible with
# INET 4.6.0 and OMNeT++ 6.1-6.4". Re-check Simu5G's WHATSNEW.md before bumping anything.
#
# NOT YET BUILT/VERIFIED: download URL patterns and the INET/Simu5G build steps are written from the
# projects' documented procedure. Expect to adjust on the first build (the stages are split so a
# failure stays local and earlier layers stay cached).
#
# PX4 / ArduPilot SITL are built in the `flight` stage at pinned upstream tags (docs/decisions/0002).

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

# ---------------------------------------------------------------- flight stacks (SITL)
# Pins: see docs/decisions/0002-flight-stacks-px4-ardupilot.md.
# Dependencies mirror the upstream setup scripts at the pinned tags, headless SITL subset only:
#   PX4        Tools/setup/ubuntu.sh --no-nuttx (Gazebo Harmonic itself comes from the sim stage).
#   ArduPilot  Tools/environment_install/install-prereqs-ubuntu.sh for jammy with SKIP_AP_GRAPHIC_ENV=1,
#              SKIP_AP_COV_ENV=1, SKIP_AP_EXT_ENV=1 and no ARM toolchains.
# The scripts are not run directly: both call sudo, and ArduPilot's refuses to run as root.
# Dropped from the upstream lists (lint/coverage/dev-only): cppcheck lcov shellcheck valgrind screen ppp
# dmidecode, and MAVProxy/pygame/wx. The gz *-dev packages are listed explicitly because PX4's CMake
# silently skips gz_bridge and its Gazebo plugins when they are missing; the final `test` catches that.
# The trees are built as root and used read-only: PX4 runs with `-w <run dir>`, ArduPilot from the run dir.
FROM sim AS flight
ARG PX4_REF=v1.17.0
ARG ARDUPILOT_REF=Copter-4.7.2
RUN apt-get update && apt-get install -y --no-install-recommends \
      astyle file g++ gcc gdb libssl-dev libxml2-utils ninja-build rsync unzip zip bc \
      python3-setuptools python3-wheel \
      libunwind-dev libeigen3-dev libopencv-dev protobuf-compiler libimage-exiftool-perl \
      gstreamer1.0-plugins-bad gstreamer1.0-plugins-base gstreamer1.0-plugins-good \
      gstreamer1.0-plugins-ugly gstreamer1.0-libav libgstreamer-plugins-base1.0-dev \
      libgz-transport13-dev libgz-sim8-dev libgz-sensors8-dev libgz-plugin2-dev \
      gawk wget python3-pexpect python-is-python3 libtool libtool-bin libxslt1-dev libpython3-stdlib \
 && rm -rf /var/lib/apt/lists/*

# Size: clone, build and clean up happen in ONE RUN per stack, so git history, object files and ccache
# never land in a layer (the first attempt filled the host disk). Before .git is removed, the exact
# commits (incl. submodules) are written to SOURCE_COMMITS.txt for the per-run manifest.
# Consequence: `make`/`waf` cannot be re-run inside the image; the stacks are run from their binaries.
# Python deps go into /opt/venv (first on PATH, so it is the python3 both builds pick up). pymavlink is
# already pinned by requirements.txt and pip leaves satisfied requirements alone.
WORKDIR /opt
RUN git clone --depth 1 --branch "${PX4_REF}" --recurse-submodules --shallow-submodules \
      https://github.com/PX4/PX4-Autopilot.git px4 \
 && pip install --no-cache-dir -r /opt/px4/Tools/setup/requirements.txt \
 && cd px4 \
 && make px4_sitl \
 && test -x build/px4_sitl_default/bin/px4 \
 && test -e build/px4_sitl_default/bin/px4-gz_bridge \
 && { git rev-parse HEAD; git submodule status --recursive; } > SOURCE_COMMITS.txt \
 && find . -name .git -prune -exec rm -rf {} + \
 && find build -name '*.o' -delete \
 && rm -rf /root/.ccache /root/.cache

RUN git clone --depth 1 --branch "${ARDUPILOT_REF}" --recurse-submodules --shallow-submodules \
      https://github.com/ArduPilot/ardupilot.git ardupilot \
 && pip install --no-cache-dir \
      lxml pyserial geocoder "empy==3.3.4" ptyprocess pexpect dronecan numpy pyparsing psutil \
 && cd ardupilot \
 && ./waf configure --board sitl \
 && ./waf copter \
 && test -x build/sitl/bin/arducopter \
 && { git rev-parse HEAD; git submodule status --recursive; } > SOURCE_COMMITS.txt \
 && find . -name .git -prune -exec rm -rf {} + \
 && find build -name '*.o' -delete \
 && rm -rf /root/.ccache /root/.cache

ENV PX4_ROOT=/opt/px4 \
    ARDUPILOT_ROOT=/opt/ardupilot \
    PX4_REF=${PX4_REF} \
    ARDUPILOT_REF=${ARDUPILOT_REF}

# ---------------------------------------------------------------- Claude Code sandbox
FROM flight AS claude
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
