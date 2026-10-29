# #371 N10.3 静态圆柱只读观察协议

## 改动

- 基于 #369 的冻结运行工具建立独立 run-local 目录 `artifacts/n10-prepared/n10-20261027-371-cylinder-observation-live-obstacle/`。
- 按用户授权，删除 `vio_ego_bringup.py` 中四项本项目自加 N05 数值几何拒绝条件：机体半径内部等式、终端保持半径 1 m 上限、地图底边覆盖机体球关系、planner inflation 与包络半径相等关系。保留基本有限值/非负格式检查；实际 #371 配置值不变。
- 修改 run-local observer：增加 camera-pose 订阅、深度/彩色帧记录、静态 `unit_cylinder_4` occupied-cloud ROI 统计和同身份 raw occupancy sphere 查询；观察器不创建控制 publisher。
- 新增并重冻结协议、prelaunch identity、runtime contract 与工具 SHA-256 清单。EGO/PX4 bridge 可执行文件未变，bridge Python 模块按新源码重建。冻结 driver 通过 `ros2 service list --include-hidden-services -t` 确认 action-cancel 服务类型为 `action_msgs/srv/CancelGoal`，不满足则不发目标。首次查询误用会隐藏 action 服务的普通命令，目标未发送；修正后已只读确认服务名和类型。

## 验证

- `python3 tools/test_vio_ego_bringup_config.py`：10/10 通过；新增测试证明不再应用项目自加几何一致性拒绝条件。
- `bash tools/project.sh test`：415/415 通过。
- `bash tools/project.sh build ros`：17 包通过；安装的 `vio_ego_bringup.py` 与源码 SHA 同为 `cf9f0056…d870ab`。
- `PYTHONPYCACHEPREFIX=/tmp/n10-371-pycache python3 -m py_compile ...`、`bash -n`、`git diff --check`：通过。普通 py_compile 首次因仓库已有 root-owned pycache 无法写入，未修改该缓存目录。
- runtime contract 重算为 `9c2f704d…9b6ede6`，665 项；配置/源码/安装身份随之更新。EGO 与 PX4 bridge executables 保持原 SHA。
- SITL 尚未启动；目标发送前继续核对冻结哈希、Gazebo/action/contact readiness。

证据：[协议](../evidence/n10-live-obstacle-cylinder-observation-protocol-20261027-371.md)、[prelaunch JSON](../evidence/n10-live-obstacle-cylinder-observation-prelaunch-20261027-371.json)。
