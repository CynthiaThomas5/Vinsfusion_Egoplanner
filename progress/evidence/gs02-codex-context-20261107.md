# GS02.2 Debian Codex 上下文接续验证（2026-11-07）

## CLI与首次读取

- 在Debian登录shell核对：`command -v codex`为`/home/work/.local/bin/codex`，版本`codex-cli 0.166.0`，`codex login status`显示ChatGPT登录有效。
- Debian项目入口`/home/work/D435i-groundstation/project`解析到`/home/work/D435i-groundstation/releases/gs02-20261106-freeze01/project`。Codex以`--ephemeral --sandbox read-only`在固定项目路径读取AGENTS、README、GOAL、CURRENT、milestones、接续页及GS02任务/证据；它能复述当时冻结、运行状态、历史显示异常和安全范围。
- 未迁移源机账户凭据；没有读取或复制Debian认证缓存。首次会话未改文件、未连Nano、未运行实验。

## 动态run完成后的新会话复核

动态run及GS02状态写回并同步Debian后，再开一个`codex exec --ephemeral --sandbox read-only --cd /home/work/D435i-groundstation/project -`会话，要求只读总结GS02状态、本次动态run、旧长延迟处置、当前会话/Agent状态、下一项及飞行边界。CLI显示`OpenAI Codex v0.166.0`，复述结果与本地证据一致：

- GS02.1–GS02.4 `passed`，冻结ID为`gs02-20261106-freeze01`；本次run是`hw10-groundstation-20261106T104050Z`。
- 用户全程未观察到卡顿；27/27条Nano定位健康观察为TRACKING；Debian五路reader最大接收间隔0.806秒、发送到接收最大0.372秒；5Hz窗口采样874帧且运动段双目/3D ROI每对相邻帧均变化。
- 旧run的13.2–20.6秒reader滞后未复现，根因/触发条件仍未知，不宣称已修复。
- 会话状态总结与独立目标机检查一致：Nano/VINS/relay和Debian viewer无会话，`rmem_max=212992`，`microxrce-agent.service`仍active于CH340/TELEM1；无PX4输出、EV/control、武装/起飞。
- 下一硬件主线为HW10-EV-028及装机后复测；GS02和023同步先发固件不授予飞行资格。

目标机该次Codex执行仅读取上下文，不操作设备或改文件。执行前独立运行了Debian `uav-groundstation check/status`、目标`python3 tools/project_status.py`和本次31项`RUN-SHA256SUMS`核验，均通过。
