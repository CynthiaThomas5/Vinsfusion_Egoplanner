# #358 N10.3 高速取消制动：启动前失败

## 结果

#358 没有进入任务 preflight。`tools/run_n10_cancel_calibration.sh` 使用 `set -u` 后，source ROS Jazzy setup 时因 `AMENT_TRACE_SETUP_FILES` 未定义立即退出。无 flight.json、无目标、无 Offboard enable、无解锁或控制样本；因此没有高速制动测量。

## 安全读回

独立运行 `tools/probe_px4_bridge_live.py --seconds 3` 后读回桥 `DISABLED`、PX4 landed=true、armed=false、control_enabled=false；车辆保持 disarmed，控制样本为0。之后只停止本次项目容器，Docker 状态为 `exited`, exit code 0。

## 处置

修正 runner shell 选项：保留 `-e` 与 `pipefail`，移除会与 ROS setup 脚本冲突的 `-u`。这只修复启动，不改变任务参数、健康旁路、碰撞规则或试验变量。用新 run id #359 按同一已冻结测量协议重开；#358 记录为 setup failure，不计量测。

## 验证

- `docker exec ... bash tools/run_n10_cancel_calibration.sh ...`：在 ROS setup 的 unbound variable 错误处退出，尚未 preflight。
- `docker exec ... python3 tools/probe_px4_bridge_live.py --seconds 3`：`DISABLED`, landed, disarmed, control disabled, zero control samples。
- `bash tools/project.sh stop n10-20261026-358-high-speed-cancel-stop`：完成；Docker exit 0。

详细机器读回保存在 `artifacts/runs/n10-20261026-358-high-speed-cancel-stop/preflight-failure-independent-readback.json`。此记录只说明安全收尾和启动错误，不是运行通过证据。
