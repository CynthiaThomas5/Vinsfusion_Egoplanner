# #527 N13正式运行总评估入口

Goal完成模式，全部N13范围保持。新增tools/debug_truth/evaluate_n13_run.py，将协议发布状态、配置哈希、运行runtime身份、N13场景启动记录/协议哈希、可见GUI窗口证据和公共核心评估统一；只有整体PASS才formal_count_eligible。缺文件判INSUFFICIENT，真实核心FAIL保留。实际#518旧单柱作为负例返回INSUFFICIENT，未产生N13正式次数。

验证：评估入口实际CLI负例运行、py_compile、python3 tools/project_status.py、git diff --check通过。产物artifacts/runs/n13-20261029-527-run-integration/negative-n12.json。尚未启动容器/飞行，协议仍draft；评估视图生成链和发布协议仍需最后集成，不声称准备已全部完成。下一步核对独立视图输出不写入原始symlink归档，完成最终发布与GUI启动。Goal保持active。
