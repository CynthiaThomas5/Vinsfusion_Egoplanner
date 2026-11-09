FROM osrf/ros:jazzy-desktop-full@sha256:fb1baede4fe42e43372588cc265c75dd06a3abdd695d85d24d013e33af7eb9a6
SHELL ["/bin/bash", "-c"]
RUN apt-get update && DEBIAN_FRONTEND=noninteractive apt-get install -y --no-install-recommends \
    python3-pip python3-venv openssh-client x11-utils mesa-utils \
    && python3 -m venv --system-site-packages /opt/uav-venv \
    && /opt/uav-venv/bin/pip install --no-cache-dir pymavlink==2.4.49 \
    && rm -rf /var/lib/apt/lists/*
COPY src/own/uav_interfaces /tmp/uav-src/uav_interfaces
RUN source /opt/ros/jazzy/setup.bash && cd /tmp \
    && colcon build --base-paths /tmp/uav-src --packages-select uav_interfaces \
       --build-base /tmp/uav-build --install-base /opt/uav-interfaces \
       --cmake-args -DBUILD_TESTING=OFF \
    && rm -rf /tmp/uav-src /tmp/uav-build /tmp/log
# Same uid as the desktop account; SSH needs a passwd entry and writable home.
RUN usermod -l work -d /home/work ubuntu \
    && mkdir -p /home/work && chown 1000:1000 /home/work
