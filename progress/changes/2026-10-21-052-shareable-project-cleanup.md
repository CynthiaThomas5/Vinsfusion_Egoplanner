# 可分享工程整理

对应[任务摘要](../../collaboration/dialogues/2026-10-21-052-shareable-project-cleanup.md)。

- 将已通过当前房间三次导航的VINS、EGO改动纳入唯一的上游提交与补丁清单；通用fetch器校验补丁和关键源码哈希，只迁入运行需要的包。VINS再增加0014构建打包补丁，移除未迁入的KITTI示例及上游launch/config安装，不修改估计算法。
- 将过去分散在运行目录的冷启动、纹理、预检、任务、只读观测和离线评价迁入tools与simulation；统一从install运行，不再source历史候选overlay。参数保持当前CPU导航组合，爬升限速改为配置自动应用。
- 清出31个未采用实验补丁、重复fetch器、失效日期绑定入口与旧参数副本，恢复路径及原哈希见[清单](../../dependencies/retired-code-20261021.json)。历史证据、大日志和旧构建仅留在ignored artifacts，不进入分享包；有效故障与坐标回归探针保留。
- 新增`tools/project.sh`，提供fetch/build/test/sim/mission/stop/export；源码分享包排除下载源码、构建产物、私人原始聊天、本地配置和凭据文件；完整本地交付同时包含已校验容器镜像。未上传、未提交、未推送。
- 首次ROS构建发现上游安装规则依赖未迁入config，已通过0014修正；首次PX4构建因容器Git目录所有权拒绝，已在构建容器内声明准确的可信目录。重试后16个ROS包及PX4构建通过。
- 标准入口首次SITL暴露PX4原生默认工作目录回到编译目录、无法找到运行副本5011机架；修正为显式`-w "$PX4_BUILD"`，禁止依赖旧二进制编译路径恰好不存在的行为。该失败运行保留为`artifacts/runs/cleanup-room-01`，未起飞。

- `cleanup-room-02`在约4.84m处触发`pose_stale`／`telemetry_stale`，已安全落地上锁，导航失败如实保留。核对原成功运行各overlay最终解析得到的21个自维护Python模块，与当前源码全部一致，没有发现遗漏的算法文件；继续使用相同参数冷启动复测，不放宽门限。

- `cleanup-room-03`完成16m飞行、驻留、落地上锁；初次自动后处理因镜像缺少matplotlib退出。将绘图设为显式可选，数值评价不再依赖绘图库；从原#246运行迁入`tools/audit_vehicle_envelope.py`，直接从SDF计算旋翼扫掠包络，取代读取旧证据数值。独立真值与9项综合复算全部通过；再以`cleanup-room-04`检查修复后的完整入口。

验证明细和范围见[本轮证据](../evidence/shareable-project-cleanup-20261021-052.md)。原#051三次冷启动成功只属于原隔离候选，不自动替代本轮重建后的飞行证据。正式P4–P6／A–H状态不因整理而升级。

最终：`cleanup-room-04`完整mission自动退出0，9项检查全通过；与03一起保留为两次新构建成功，02超时失败不隐藏，不升级正式稳定性验收。16包／PX4编译、133项回归、结构／解压检查均通过；本地完整分享包含固定镜像，仿真已关闭。CURRENT和工程整理里程碑已更新，原暂存状态未重写。
