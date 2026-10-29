# #286 N08 前向走廊方向证书

## 范围

父目标 N08 保持 `in_progress`，执行模式为用户指定的 N08 Goal 完成模式。当前子项是恢复普通前向单目标起飞后准入；不包括显式返航或实机。普通目标仍在到达、停车／保持后结束。

## #285 证据与缺口

`n08-cancel-translation-prescan-20261026-285` 的 N05 扫描、释放后准入、ground full-symmetric corridor、只读 preflight、runner／#276 二进制指纹均通过。起飞并稳定后，fresh same-identity airborne map 的首个对称球内有 32 个 rear unknown、0 occupied；任务 goal 尚未发送，未产生曲线、取消、停车或制动测量。直接 PX4／bridge 读回为 landed、disarmed、control disabled，项目运行已停止。原运行保持 FAIL，见 [#285 诊断证据](../evidence/n08-airborne-forward-corridor-unknown-20261026-285.md)。

## 实现

- `tools/n08_trial_gate.py` 增加只适用于单段前向无偏航任务的 swept-volume 证书。完整 body inflation 与 0.25 m margin 数值不变；查询球按 0.075 m 向前放置，25 mm 最大采样间隔及半步覆盖不变。起点采用独立 hold 查询，终点保留未平移、全向 `body + 0.25 m` hold 查询。unknown、occupied、outside、查询资源和 freshness 判据未放宽。
- `tools/run_n08_braking_trial.py` 起飞后使用该方向证书；ground pre-enable 仍使用完整对称 N08 corridor。普通 forward EGO 样条继续受 5 cm 连续管道限制，并增加 `x >= 0` 的不倒退条件；水平／垂直管道、0.15 m 实际 tracking watchdog 与 0.12 m/s 速度上限不变。return/yaw 动作仍走原对称证书。
- 更新 runtime fingerprint：两个工作区 Python 运行文件都必须与本次 cold-run manifest 匹配，#276 编译源码／二进制仍单独严格核对。
- 在 #285 的 airborne raw map 上离线重放：旧 symmetric 首球 32 unknown；新证书 25/25 raw free、0 unknown／occupied，start hold 与 symmetric terminal hold 通过；曲线／跟踪几何上界余量 0.02236 m，hold 余量 0.025 m。同图候选 landing 几何离线检查 21/21 通过。报告只作离线实现证据，不计飞行通过。

## 验证

- `bash tools/project.sh test`：346 项单测通过，navigation-adapter integration 通过。
- N08 几何 helper 定向测试：18 项通过；包含后方未知可通过、前向／可达未知拒绝、普通曲线不倒退约束和终点 hold 检查。
- in-memory Python `compile()` 与 runtime manifest 哈希比对通过；manifest 包含当前 `tools/n08_trial_gate.py` 和 `tools/run_n08_braking_trial.py` 哈希。
- `git diff --check` 通过。
- 无编译 ROS／C++ 改动，不重建 EGO；当前仍须 SITL 证明实际目标、取消停车和 hold。

## 下一步与未解项

启动全新 `#286` 冷运行，重做已通过配方的 N05 纯平移支架扫描与 fresh post-release admission；只有 N05、40 s preflight、地图身份／健康／时间、profile 与 runtime 指纹全通过才运行 `single_goal motion_cancel 0.04 0.06`。必须观察 caller cancel 三字段、replacement stop spline、旧轨迹不恢复、停止速度／距离、保持与 destination landing，并独立读回 landed/disarmed。

普通同版本三次 `terminal_stop`、对 hold／compute-only／execute 证据审计、制动与延迟预算、N05/N06 预算回填仍未完成。当前离线重放没有 N08 运行通过。
