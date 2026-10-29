# #387 N10 方箱与实际轨迹坐标复核

对话摘要：[2026-10-27-387](../../collaboration/dialogues/2026-10-27-387-n10-obstacle-alignment-forensics.md)。

## 变更

- 新增只读工具 `tools/debug_truth/evaluate_n10_obstacle_alignment.py`，用固定 prestream SE(3) 对齐 #385 的 SDF 方箱、完整 B 样条、时间戳 PositionCommand、raw map 查询与已归档全机采样净空。
- 新增 #387 机器报告与说明；不修改 flight/runtime/control 参数。
- N10.3 仍未通过；N10 父状态保持 `in_progress`。

## 验证

- `python3 -B - <<'PY' ... compile(...) ... PY`：取证脚本内存语法编译通过。
- `python3 -B tools/debug_truth/evaluate_n10_obstacle_alignment.py artifacts/runs/n10-20261027-385-arrival-dwell4-retry`：产出 `n10-obstacle-alignment-forensics.json`。
- 固定变换后 expected box odom pose 与 SDF world pose 相差 0.264 m；活跃 PositionCommand 到箱体最近 1.463 m；全机真值采样扣除观测样本间位移后净空 1.131 m。
- 注入后 0.5/1.25 sim s 的箱体内部查询均为 free=160、unknown=0、occupied=0。occupied ROI 记录属于静态圆柱观察，不与动态方箱对应。

## 局限与下一步

整条 B 样条几何仍穿过箱体空间，但时间戳活跃命令中心线未穿过；不能把完整曲线当作已执行轨迹。free 查询的地图语义／更新机制尚未解释，现有 ROI 未保存点坐标。下一项 #388 先审计 query 服务与地图占据更新实现，准备仅观测表面、内部、source stamp 与 map identity 的可复算记录；若源码/历史数据已解释结果，不重复飞行。
