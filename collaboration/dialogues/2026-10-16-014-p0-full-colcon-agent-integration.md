# P0 全仓构建与 Agent colcon 集成

- 继续目标：完成 GOAL.md A–H 与 P0–P6；本条只记录新增的整仓静态构建证据。
- 用户约束：保护既有修改；第三方修复记录基准 commit、补丁顺序与哈希；构建成功不能冒充运行、SITL 或实机验收。
- 从官方固定 commit 重建 Agent/spdlog 源码并应用两份仅影响 `colcon.pkg` 的补丁；补丁后的源码清单与 vendor checkout 逐项匹配。
- 在派生镜像 `sha256:099ab9afecd28b7354f6d649b3384b1db30c7c67c973e9b93b03f87aca7ad6f8` 中，用新 build/install 目录构建 15 个 ROS 包，全部通过。
- 未启动 Agent 服务或 PX4；未运行 ROS tests、launch、DDS graph、PX4 固件、SITL 或实机。
- 下一步：固定并导入 PX4 v1.17.0 完整源码及子模块，再构建 SITL firmware 并核验 Agent DDS 运行互通。
