# N10.3/#458 综合正常导航校准准备

对话摘要：[2026-10-28-458](../../collaboration/dialogues/2026-10-28-458-n10-integrated-maxcnt220.md)。

- 从 #436 复制独立校准工具到 `artifacts/n10-prepared/n10-20261028-458-maxcnt220-integrated/`，绑定新 run/protocol/prelaunch 身份；未改写 #436 归档。
- 删除副本中的长时 fault-path 探针启动行，以遵守用户 #434 排除故障与故障后校准的决定；不注入故障。正常状态、接触、资源、VIO、地图、跟踪和独立安全末态观察仍保留。
- 只把 `config/components/localization/vins_sim.json` 的 `max_cnt` 从 180 改为 220，依据 #457 严格 native 输入离线回放；参数是待综合校准候选，不是部署或冻结。验收门限未改。
- #458 prelaunch 将额外验证 VINS `session.json` 的 settings hash 与生成 `vins.yaml` 中的 `max_cnt`；完成运行后按实际代码和平台证据评估。
- 增加 prelaunch 对 source config SHA、session settings SHA、generated `vins.yaml` SHA 与 `max_cnt: 220` 的绑定检查；驾驶脚本要求这些核对通过才继续。
- `python3 -m py_compile ...prepare_prelaunch.py ...n10_live_obstacle_injector.py`、`bash -n ...n10-runtime-driver.sh`、协议候选/无故障探针/阈值未改断言及 `git diff --check` 均通过。
- 仿真尚未启动；实际运行和评估结果待本子项继续后补记。
