# #307 N08 后向保持短时静态profile

- 复制#306 rear-view路线，仅将rear yaw=−π的静止保持12秒缩为4秒；turn-in、回中−π/2→0、其余路线与所有门限不变。总时长少8仿真秒。
- 假设：#306在rear视角已到达后回中时cost=1.0312，缩短rear dwell可保留健康余量并完成支架释放准入。
- `python3 -m unittest tools.test_preflight_scan` 41/41；JSON、shell、项目结构、diff check通过。尚无SITL资格。

证据：[静态报告](../evidence/n08-negative-y-rear-short-hold-profile-20261026-307.md)。
