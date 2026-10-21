# P0 派生容器与整仓干净重建

- 任务日期：2026-10-16
- 对话摘要：[P0 派生容器重建](../../collaboration/dialogues/2026-10-16-012-p0-container-rebuild.md)
- 文件变化：修正 `docker/Dockerfile.vins` 的基础镜像引用；更新构建说明；在 `dependencies/sources.json` 记录本机基础镜像 ID 和当前锁定范围；新增派生容器与整仓构建证据并更新 CURRENT、P0 阶段和 A 清单引用。
- 行为变化：Dockerfile 现在使用本机 repo digest `px4-ros2-gz@sha256:fbdf66eb12efdea888acdafeb501280fa108513ae6b7703fe2a699ba97989f8e`，构建说明会先断言本地 tag 解析到锁定 image ID；构建上下文改为 `docker/`，避免传输多 GB 工作区。
- 验证：保留裸 image ID `FROM` 的失败记录；digest 引用执行 `docker build --no-cache --progress=plain -f docker/Dockerfile.vins -t d435i-vins:dev docker` 成功。随后使用来自同一基础 image ID 的无缓存派生镜像、新 build/install 目录执行整仓 colcon build，13/13 包完成，退出码 0。
- 证据：[派生容器及整仓干净重建](../evidence/p0-clean-container-build.json)。构建原始日志、包清单与哈希位于 `artifacts/runs/p0-container-rebuild-20261016-01/` 和 `artifacts/runs/p0-clean-container-build-20261016-02/`。
- 局限：基础镜像仍只有本机缓存且没有本项目的重建来源；完整 ROS/OS 传递包与 apt 快照未锁；没有运行 package tests、launch、回放、PX4、SITL 或实机测试。因此 A、P0 仍 pending/in_progress。
- 下一步：继续闭锁基础环境和 PX4/Agent 互通依赖，再做 P0 源码及 DDS/SITL 验证；不得据此开始自主飞行。
