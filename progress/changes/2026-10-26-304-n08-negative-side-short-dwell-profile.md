# #304 N08 负侧观察驻留时间静态变体

- 新增负 Y 侧视 profile，严格复制 #302 负侧 profile，仅将 yaw−π/2 的第二个同姿态阶段从18秒缩为8秒；转向、yaw回中、回收及全部健康／地图／几何门限不变。
- 新增 profile 白名单与单变量回归测试。
- `python3 -m unittest tools.test_preflight_scan`：38项通过；`bash -n`、JSON解析、`python3 tools/project_status.py`、`git diff --check`通过。
- 运行资格尚未建立；下一步为一次全新 #304 SITL，按现有 N05 与 N08 门控条件执行。

证据：[静态报告](../evidence/n08-negative-side-short-dwell-profile-20261026-304.md)；profile 位于 `config/components/simulation/preflight_scan.json`。
