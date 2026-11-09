# 固定依赖

`dependencies/sources.json` 是唯一版本与补丁应用清单。`tools/fetch_dependencies.py` 验证commit、补丁SHA256、许可文件和关键修复文件；临时目录重建成功后才移动至目标，已有目标一律拒绝覆盖。

```bash
bash tools/project.sh fetch
# 只获取某个缺失依赖
python3 tools/fetch_dependencies.py --source ego_planner
```

ROS依赖：VINS只物化camera_models／vins，EGO只物化5个规划包，另有px4_msgs、Agent和spdlog；PX4保持独立的固定源码及递归submodule gitlinks。旧实验区是只读来源，不被构建或启动器引用。

本次有效VINS链为0001–0005→0009→0011–0019；其中0014仅作构建打包，0015–0019增加只读回环／残差诊断，不改变生产定位数值。EGO链为0001–0011→0017–0019→0021→0035–0043→0045–0049→0050–0053。逐项哈希与应用上下文以`dependencies/sources.json`为准。0044曾加入最终样条动力学复核及硬拒绝，现已按用户要求从有效链移除；0053继续移除项目自加的整条曲线raw occupancy／地图就绪准入，并恢复上游规划失败重试。EGO本身的膨胀占据碰撞、轨迹碰撞回调、深度超时和紧急停车仍保留。运行代码恢复上游的一次可行性检查和一次时间重分配流程。0045为EGO定点航向轨迹；0048让简单航点统一走带身份／地图校验的NavigateToPose action；0049按官方 EGO 规则使用膨胀占据层，raw unknown 不单独判碰撞；0050只为上游原有可行性检查输出诊断数据，不改阈值或轨迹。取消停车与 N08 低速测量仍限于各自报告的范围。没有把全部历史候选叠加进运行源码。未采用的补丁已移出活跃树，恢复位置和哈希见`retired-code-20261021.json`，其本地归档不属于运行输入。

第三方许可独立保留。房间源`ego_world`的上游未声明许可，不能将其标成已获GPL或其他授权。固定容器的可移交归档与约束见[构建环境](../docker/README.md)。

## N17许可证核对

7个src/own ROS包的package.xml已经声明Apache-2.0，整理保持这些现有声明，并提供[许可证全文](licenses/Apache-2.0.txt)。旧README“自维护未指定许可”的概括与包级声明不一致，以实际包级声明为准；未据此给所有工具、文档、场景或第三方文件另授一份全仓库许可证。

VINS和EGO的GPL、PX4/px4_msgs的BSD、Micro XRCE-DDS Agent的Apache、spdlog的MIT按sources.json与各自LICENSE保留，补丁的派生版权和应用顺序不变。默认ego世界的锁定上游未声明许可，这一事实仍明确保留，不将其改标为Apache或GPL。发布不改变现有仓库访问权限；接收方需要取得仓库及固定环境分支的访问权限。

## #592 250级仿真派生模型

EGO补丁0061在0060后应用，只开放map_resolution，默认保持旧配置0.1m；当前项目配置显式传0.15m。独立fresh目标已重建全部补丁并校验文件哈希。PX4来源不改写；本地模型派生、许可、网格引用和重生成见[模型说明](../docs/quad250-simulation.md)及`quad250-model-provenance.json`。

## #599 NavRL floorplan2静态场景

`navrl_floorplan2_world`为随源码跟踪的数据资产，不是新增ROS包，不执行NavRL控制代码。原文件`ros1/uav_simulator/worlds/floorplan2/floorplan2_static.world`按commit3725bcc2e7c1be4ecf1455d922299ae85042603a原字节迁入simulation/worlds/navrl，diff为空；SHA256和该子包MIT许可见sources.json与licenses/NavRL-uav_simulator-MIT.txt。运行合成由自维护prepare_px4_vio_bootstrap_world.py完成，原静态碰撞几何保持，材质适配及PX4系统合成的输出SHA256记入run/world.json。不引入其人物mesh、预建PCD、机器人、策略、ROS1节点或真值话题。


## #600 NavRL 多柱静态场景

`navrl_pillars_world`从上述NavRL固定commit的`generated_env/generated_env_static.world`原字节迁入，源模型含30圆柱与30方柱，但仅定义视觉、没有柱体碰撞。pillars场景启动时逐个依据视觉primitive添加匹配的静态碰撞几何，并应用自然色材质；登记的源world保持不变。MIT许可沿用`licenses/NavRL-uav_simulator-MIT.txt`，源文件SHA与材质生成记录在sources.json及运行证据中。

### HW06 ARM/Foxy 2026-11-03

硬件链仍以EGO commit `23a8d5a191711dd65633df689bd00f55d4dea8f9`为基准、保留GPL-3.0-only。
0062修正前序cstddef新增后的patch上下文；0064删除已经被0048移除的waypoint订阅修改段。
0066在0065后应用，修正原生时间重分配只延长中间knots、短轨迹完整时长倍率不足的问题；
完整knot时间轴同比缩放，manager原有端点导数重拟合保留。未恢复0044或新增曲线硬拒绝门。
6/9/20控制点的实际C++回归验证完整时长、几何对应、导数缩放与原生可行性条件；Nano安装库也通过。
基准、应用顺序、补丁和最终文件SHA256均以sources.json为准。
这是数值行为变化，当前只推进HW06地面计算验证，不把历史SITL/飞行资格继承到新补丁。

硬件TELEM1串口帧重同步补丁与只读基线重链接入口见[Agent硬件补丁说明](patches/agent/HARDWARE.md)。该配置独立于冻结仿真Agent默认补丁列表；真实时效验证和局限以DDS-LATENCY-006证据为准。
