# P0 派生容器重建

- 目标仍是 `GOAL.md` A–H 与 P0–P6 全部完成；本摘要记录 P0 容器与重建路径的决定。
- 用户约束：旧工程和真实设备保持只读；每次构建使用独立产物目录；不得把编译结果描述成运行或验收通过。
- 发现原 Dockerfile 将裸 `sha256:<image ID>` 写在 `FROM`，Docker 把它解析为远端镜像仓库引用；项目依赖的基础镜像实际在本机，仓库名为 `px4-ros2-gz:jazzy-harmonic`。
- 将 Dockerfile 改为本地仓库 digest 引用，并在构建说明中校验对应 tag 的固定 image ID；Dockerfile 不复制项目文件，因此构建上下文采用小型 `docker/` 目录。
- 基础镜像没有项目内重建配方且只在本机。派生镜像和整仓重建结果保存在对应 `progress/evidence` 报告与 `progress/changes` 记录；本对话摘要不作为验收证据。
- 待办：获取/整理基础镜像来源或可分发归档，闭锁完整 OS/ROS 传递依赖；PX4、XRCE Agent 和 DDS/SITL 运行验证仍待后续完成。
