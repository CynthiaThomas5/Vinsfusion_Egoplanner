# #305 N08 负Y视角替换静态profile

- 新增 profile，完整复用#300已完成并通过post-release N05的 overhead/free-sector路线；仅将原+Y侧观察两阶段改成−Y水平观察，保持12s+18s时长与全路线时间。回中、下降和门限不变。
- 该变体对应#300地图中forward capsule的负Y薄层unknown；避免在长路线尾端追加额外视角驻留。
- `python3 -m unittest tools.test_preflight_scan` 39/39通过；JSON、shell语法、`project_status.py`、`git diff --check`通过。
- 未产生SITL或飞行通过；下一步新冷启动并服从同一N05/N08门控。

证据：[静态报告](../evidence/n08-negative-y-side-window-profile-20261026-305.md)。
