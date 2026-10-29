# #306 N08 后向观察与分段回中profile

- 添加从#305路线导出的后向观察profile：yaw0→−π/2→−π，rear hold12秒；再经−π/2→0回中，随后按原路线下降。相比#305增加24仿真秒。
- 假设来源为#305 same-identity raw map后向薄层unknown及#233后向start-hold unknown；不改N05/N08地图、健康、速度、空间或跟踪门限。
- `python3 -m unittest tools.test_preflight_scan` 40/40；JSON、shell语法、`project_status.py`和diff check通过。
- SITL仍待执行，不能计为准入或飞行通过。

证据：[静态报告](../evidence/n08-negative-y-rear-view-profile-20261026-306.md)。
