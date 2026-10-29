# N06.5 r28 单轴平移入口观察 pilot

日期：2026-10-23。Goal 完成模式，范围 N06。父目标 N06/S4 保持 `in_progress`。

## r28 结果

r28 在 wall layout 和 N06 textured surround 内，使用现有 `n06_x_visibility_slow.json` 做单轴 X 后退／回程；truth 从 x=0 后退至 `-2.39448 m`，最终回到 `x=0.01056 m`，truth yaw 全程 `0°`。运行记录区间为 sim `5.021–98.042 s`。101 秒请求的 recorder 实际持续104.087秒，记录3,012组depth/camera-pose和1,506条optimized odometry；2,019条LocalizationStatus全部有效，444条MapStatus始终是同一epoch/map_id的`ready`，无health lock或map reset。Runner exit 0，项目容器和匹配进程已停止。

三张 live plan_env snapshot保持相同epoch=`f959557280b0425caaf8ee8f53d39886`、map_id=`…-1f140b88787042deabf2b84f5eb90af6`与frame；source age为0.116／0.099／0.145s，fusion age为0.039／0.042／0.041s。每张snapshot的错误epoch和map_id拒绝检查均通过，archive readback exact。

对snapshot raw occupancy使用生产 `querySphere` 闭格查询函数，在live probe实际VINS位置`[0.049815,-0.003884,-0.006706] m`复算：N05 body球半径0.730618m的三张结果均为`free`，各2,195 free／0 unknown／0 occupied cell；终端hold邻域半径0.980618m均为`free`，各4,923 free／0 unknown／0 occupied。身份／新鲜度稳定，说明此后退再回原点的观察流程在wall仿真 snapshot中首次得到明确的body与hold free证据。

在线一次body球服务查询仍返回`no_fresh_fused_depth`，尽管probe前后MapStatus为ready且source/fusion age为0.099／0.002s；此单次请求没有正向服务响应，需保持为待解释的瞬时查询缺口。Probe随后发送默认目标`[+0.5,0,+0.5]m`，EGO以`full_curve_terminal_hold_occupied`拒绝，0条曲线、0条迟到曲线。不是地图身份或定位失效：对snapshot-03的精确离线raw query显示该默认目标的hold球内有5个occupied、0 unknown；从起点到目标的body扫掠可通过，只有terminal hold被占用。probe的图中无PX4／bridge／controller／traj_server／setpoint或控制publisher。

为选择下一目标，在相同snapshot-03上再复算一个离线候选：相对实际VINS起点沿Y平移`+0.6m`，terminal hold为4,923 free／0 unknown／0 occupied，直线body sweep以0.5m/s provisional bound通过25次查询。它还不是EGO曲线或在线通过，仅作为下一次planner-only目标输入。完整逐项结果见[机器replay](../../artifacts/runs/n06-20261023-wall-r28/n06-body-hold-replay.json)。完整快照、日志、输入与哈希见[运行目录](../../artifacts/runs/n06-20261023-wall-r28/)。

大范围 `analyze_n06_snapshot_sweep.py` 的候选链穷举在约两分钟CPU计算后中止；本报告只声明可复现的精确body／hold球查询及两个目标的定向直线扫掠结果，不声称完成全地图候选链搜索。原始unknown策略、N05包络／预算和N06验收条件均未改变。

## 下一项：r29 live EGO lateral goal

r28证明wall起点body／hold球在raw map中可为free，但内置planner probe选中的抬高目标被5个occupied hold cells正确拒绝。下一次保留相同X观察profile、wall布局、纹理surround及fresh-snapshot流程，只把planner-only目标改为相对live VINS起点`[0,+0.6,0]m`。目标终端hold和起点至目标body直线扫掠都已由r28快照做离线精确查询并通过。唯一主要变量是goal offset；判据为实际EGO在同一fresh map identity下发布匹配goal的B-spline full-curve证书，且没有fault后迟到曲线。仍无controller或trajectory consumer。

```bash
bash tools/run_n04_map_layout.sh n06-20261023-wall-r29 wall_box_column 92 motion_n06 config/components/simulation/n06_x_visibility_slow.json
```

在r29 `snapshot-01` metadata出现后、snapshot间隔内，容器内运行自定义planner-only probe，输出保存为`n06-live-layout-probe-lateral.json`：

```bash
docker exec -w /workspace d435i-n06-20261023-wall-r29 bash -lc 'source /opt/ros/jazzy/setup.bash && source /workspace/install/local_setup.bash && export FASTRTPS_DEFAULT_PROFILES_FILE=/workspace/config/middleware/fastdds_local_shm.xml && python3 tools/probe_n06_live_layout.py --run-id n06-20261023-wall-r29 --target-dx-m 0 --target-dy-m 0.6 --target-dz-m 0 --observe-s 3 --output /workspace/artifacts/runs/n06-20261023-wall-r29/n06-live-layout-probe-lateral.json'
```

The runner's default probe remains recorded separately. r29 does not close N06; a live curve still needs both layouts and the full hold／handoff／fault matrix.
