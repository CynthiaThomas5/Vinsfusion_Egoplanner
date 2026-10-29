# N06.7 r30 corridor 入口与局部地图边界诊断

日期：2026-10-23。Goal 完成模式，范围 N06。父目标 N06/S4 继续 `in_progress`，`next_goal=N06`。本轮完成 corridor 第二布局的传感器观察与 planner-only 拒绝诊断；N06 两布局曲线出口未通过。

## r30 运行

命令：

```bash
bash tools/run_n04_map_layout.sh n06-20261023-corridor-r30 corridor_box_column 93 motion_n06 config/components/simulation/n06_x_visibility_slow.json
```

Runner 自然 exit 0；本次恢复时确认匹配容器和运行进程已停止。运动真值记录只作离线运动概况：X 最远 `-2.3983 m`，最终 `+0.0079 m`，yaw全程0°。输入记录104.472秒，包含2,998 depth/camera-pose对、1,499条优化里程计、1,569条实际fused trace；2,018条LocalizationStatus全部valid，440条MapStatus均为同一epoch/map_id/frame并保持ready。

三张快照共享epoch=`0e3d604fd3a649e29ed082707f3c8c4a`、map_id=`0e3d604fd3a649e29ed082707f3c8c4a-d7a2031f85c54a0b928caa9065669e79`及匹配frame。source/fusion age依次为0.086/0.027、0.109/0.028、0.094/0.034秒；错误epoch与map_id拒绝均通过。原始档案SHA见[机器报告](n06-corridor-observation-boundary-20261023-105.json)。

## 候选门与默认 probe

Snapshot-01实际VINS起点body球为2,196 free／0 unknown／0 occupied。只测试后退 `−0.8/−1.0/−1.2/−1.4 m`，使用生产闭格球／连续扫掠helper。四条路线首次都在相同扫掠sample（index 11，x≈−0.260m）遇到4个unknown cell；四个终端hold分别含1,701／2,367／3,034／3,687个unknown。所有候选occupied均为0，因raw unknown fail-closed而没有选出候选，**没有发送自定义goal**。

Runner随后独立发出内置默认planner-only目标`(+0.5,0,+0.5)m`。此时map ready且fresh（source/fusion age 0.111/0.050秒）、identity稳定；live body query为2,196 free／0 unknown／0 occupied。EGO未产生曲线，返回`full_curve_planning_failed`；0条迟到曲线。图中没有PX4／bridge／controller／traj_server／navigation supervisor或控制topic。Snapshot-03在记录到的VINS pose下，当前body球raw free；当前terminal hold为4,863 free、16 unknown、25 occupied，符合hold体积碰到corridor入口侧壁并含少量未知的拒绝。

## unknown 的证据解释

我对候选首个扫掠失败的4个voxel center复算了同stamp输入：它们在历史相机视角中曾入图。逐帧同stamp融合trace筛出610／270个有效depth-pose对；离线按当前plan_env DDA逐像素重放时，每个unknown体素被相应射线穿过610／270次（上下两层计数不同）。但该快照拍于传感器从后退扫描返回x≈0之后，不能据此认定raycast缺陷。

当前运行参数`local_map_margin=10`体素，resolution=0.1m；`clearAndInflateLocalMap()`会把当前局部更新边界之外的占据重置成unknown。回到x≈0、镜头朝+X后，x≈−1.05m这些cell处在约1m局部保留边界之外，和快照unknown吻合。此为源代码、参数和快照共同支持的解释，但没有保存逐帧occupancy历史，故标为证据推断；unknown保持拒绝。

候选扫描记录终止于sim 103.060s，而snapshot-01 fused source为106.426s，缺3.366秒精确相机pose；snapshot-03 source比最后记录pose晚16.830秒。标准覆盖工具因此因缺少source-time pose退出；我保存的补充投影与DDA报告都显式注明该时间限制。补充DDA回放也不是C++节点重放或occupancy历史证明。

## 下一子项 N06.8 / r31

新证据支持的假设是：在 corridor 入口外保留当前相机位置于`x≈−0.8m`，使局部地图的1m margin覆盖完整候选hold；同时从`x≈−3.2m`面向+X观察，使半径0.981m的终端体积处于入口前开放区。下一次只做 sensor-only 单轴X退后／停稳／部分回程，不改map margin、unknown策略或N05预算。若精确raw body、整段body sweep和目标terminal hold全部free，才发送`(0,+0.25,0)m` planner-only目标。

候选配置和命令见[#105改动记录](../changes/2026-10-23-105-n06-corridor-observation-boundary.md)及[机器报告](n06-corridor-observation-boundary-20261023-105.json)。N06原两布局完整扫掠、hold/emergency hold、replanning handoff及故障拒绝出口均保持未完成。
