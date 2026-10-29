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

## 跨 Docker 存储后端的身份校验（N17）

相同镜像经docker save/load，Docker可能分别显示OCI index digest或单平台image/config digest。N17实际空引擎导入已观察到原ID099ab9af…变为1ec91baf…，但Architecture、Os、完整Config及全部RootFS层digest完全相同。启动入口以config/runtime.json的image_content_sha256验证这四部分规范JSON，不接受只同名的镜像；任何文件层、启动配置或架构变更均拒绝。原image_id保留追溯。

`python3 tools/check_container_image.py`可独立显示实际ID及固定内容指纹。当前归档为Linux amd64；ARM和未验证GPU/驱动组合不在现有迁移资格内。导出器在旧归档不存在时，可从已精确验证的本地固定镜像生成新归档，输出manifest和SHA256SUMS；旧归档存在而校验失败时仍拒绝。
