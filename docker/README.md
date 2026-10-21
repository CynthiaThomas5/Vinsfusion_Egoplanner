# 固定运行环境

当前基线使用`d435i-vins:dev`，镜像ID由`config/runtime.json`校验，包含ROS2 Jazzy、Gazebo Harmonic、OpenCV4.6、Ceres2.2及PX4构建工具。NVIDIA只承担渲染；没有切换CUDA定位／规划。

分享包附`container-images.tar.zst`，在包目录执行：

```bash
sha256sum -c SHA256SUMS
zstd -dc container-images.tar.zst | docker load
tar -xzf project-source.tar.gz
cd project
bash tools/project.sh fetch
bash tools/project.sh build
```

原始固定镜像归档的路径／SHA256及Debian版本清单保留在`dependencies/sources.json`。归档提供可移交的二进制环境；原始基础镜像没有公开可追溯构建配方，不能宣称仅凭Dockerfile即可在任意空机器从零重建环境。`Dockerfile.vins`保留派生层配方。接收方仍需NVIDIA宿主驱动、容器工具和网络获取固定源码；异机运行与实机不在本机复测结论内。

`tools/project.sh`构建只使用当前源码和单一install；仿真服务器显式headless-rendering／NVIDIA EGL，窗口用`run_gpu_viewer.sh`选择PRIME/GLX。运行产物从空PX4状态开始，不复制历史BSON／任务状态。
