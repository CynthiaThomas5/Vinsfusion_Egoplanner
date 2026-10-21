# P2 深度断流注入

- 用户要求继续按 P0–P6 推进；本轮选了可独立验证的深度输入故障注入。
- 复用 `tools/fault_relay.py`，将 `depth` 加入现有 source-header-stamp 中继，并增加深度 topic 路由单测。
- 从 Gazebo D435i 采集 `/clock` 和 `/sensors/d435i/depth` 后，在两个独立 ROS domain 中分别回放同一 bag，按各自首帧 stamp 注入 5 秒深度断流。
- 两次窗口均观察到断流前转发、窗口内丢弃、窗口后恢复转发，分别丢弃 51 帧和 47 帧。证据为 `progress/evidence/p2-depth-dropout.json`。
- 采集记录有局限：第一次脚本尝试在 ROS setup 前启用 nounset，未启动；修正后后台 recorder 忽略了脚本发出的 SIGINT，实际记录约160秒，并报告传输丢帧，随后通过明确 TERM 停止。bag 仍用于注入验证，不用于频率或完整性验收。
- 当前没有运行地图消费者；深度过期检测、旧地图失效、PX4 状态行为均未验证。此记录不代表 P2 或 E 条目通过。
