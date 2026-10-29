# #209 N08.2a：计算但保持 launch 接线

- 文件：VIO/EGO launch 增加 `bridge_compute_only` 参数；PX4 bridge 单节点 remap；host/runtime 支持 run-local planner 参数与模式输入；新增 remap contract helper 和回归用例。
- 原因：N08 需要将 EGO 轨迹计算与 bridge 实际执行分开，以固定 hold 为对照。原启动流程只有直接执行路径。
- 验证：ROS build 17/17 包通过；`tools/project.sh test` 281 项通过，导航 adapter 通过；Python／shell 语法与父子 launch `--show-args` 通过；`project_status.py` 和 diff check 通过。
- 局限：未运行仿真或 flight；没有 run-time graph／取消／hold 证据，不代表运动边界已建立。
- 下一步：N08.2b 实现明确的 compute-only 单目标、采样 READY 轨迹、立即取消、确认 hold 和安全落地；随后再建立运动停止边界。
- 对话摘要：[N08.2a #209](../../collaboration/dialogues/2026-10-24-209-n08-compute-only-mode.md)
- 证据：[模式接线报告](../evidence/n08-compute-only-launch-mode-20261024-209.md)
