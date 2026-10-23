# #074：逐候选几何验证诊断

[对话摘要](../../collaboration/dialogues/2026-10-22-074-loop-candidate-diagnostics.md)。保护开始前未提交修改；仅实施用户批准的第6个小目标。

## 改动

- 第三方固定上游新增`dependencies/patches/vins/0019-loop-candidate-diagnostics.patch`，基于VINS提交`72023bc5d2abb14faa4c02a5c040d84f996b587a`及0018。`findConnection()`仅填充观察数据：BRIEF匹配数、PnP输入／`solvePnPRansac`返回值／内点数、相对yaw和平移以及现有判定结果。原有`>25`、`abs(yaw)<30°`、`translation norm<20m`条件保持不变；Fundamental RANSAC仍禁用。
- 每次回环候选在已有只读status中按批输出。单批上限512，溢出数显式记录。`tools/diagnostics/record_loop.py`将批次聚合至`loop-observation.json`，状态JSONL仍保留批次本身。
- `dependencies/sources.json`登记补丁顺序、补丁哈希和修改后vendor源码哈希；VINS补丁README增加行为与限制说明。

## 验证与实验

- 完整`python3 tools/fetch_dependencies.py --source vins_fusion --target <fresh-temp>/vins_fusion`从固定提交应用0019及全部前序补丁成功，源码哈希匹配。
- `bash tools/project.sh build ros`：17个ROS包完成，`loop_fusion`成功重编。仅有该包既有的signedness及VLA警告。
- `bash tools/project.sh test`：199项单测通过，导航ROS action集成通过（250Hz时钟下最大pose receipt age为0.053秒）。`git diff --check`通过。
- `real-loop-20261022-074-01` fresh epoch在第29/47段触发原定位健康门`normalized_cost_exceeded`（q=1.1243）；9候选记录完整，探针FAIL保留。1486条VehicleStatus样本仍DISARMED。支架安全复位、收到detached与移除确认，独立模型清单无支架，后端正常退出；该试次不计入完整路线统计。
- `real-loop-20261022-074-02` fresh epoch完成47/47段，支架探针结果`unarmed_support_loop_revisit_completed`，1486条状态样本均DISARMED。101关键帧产生50个候选、4条验证边及4次优化；50个连续事件全部记录、`dropped=0`，事件数与候选计数一致，accepted数与验证边计数一致。
- 阶段分布：45/50因PnP内点数`<=25`被拒，其中14次PnP函数返回false（均为0内点），31次返回true但内点不足；1/50通过PnP内点门后因yaw `67.7775°`超过原30°条件被拒，平移`4.9581m`通过原20m条件；4/50通过。BRIEF匹配数为57–109，故这轮没有候选止于描述子匹配数量门。
- `tools/debug_truth/evaluate_fixture_loop.py`在正常后端退出后通过全部13项：4条边独立几何误差为平移1.82–3.50cm、姿态0.109–0.317°；观察器无控制／TF输出、没有订阅真值，队列与曝光配对检查通过。

## 限制与下一步

这是单一理想仿真房间的未武装物理支架路线。第一个fresh epoch健康门中止，第二个完成；两次记录均保留且分开分析。诊断没有保存完整图像或逐特征对应关系，也没有改变估计器、匹配、门限或控制链。此次只说明候选在哪一阶段被拒及实际回环几何，不说明回环降低了raw VINS漂移，更不构成“不漂移”保证。

建议下一小目标：只用074-02已有raw与回环修正轨迹、debug_truth做一次离线漂移比较，固定初始静止姿态对齐与尺度1，不作闭环后重对齐；等待用户批准后实施。

运行数据与哈希见[验收报告](../evidence/loop-candidate-diagnostics-20261022-074.md)及`artifacts/runs/real-loop-20261022-074-{01,02}/`。正式里程碑未升级。
