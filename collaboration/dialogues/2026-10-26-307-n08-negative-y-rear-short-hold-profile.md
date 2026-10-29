# N08 #307 后向保持时长变体

## 依据
#306 后向yaw−π已到达，完成12/17阶段；在回中yaw−π/2时cost=1.031188越过原1.0门限。后向地图效果无post-release快照，不能判断。

## 决策
#307只将rear-facing静止hold从12s缩为4s，turn、return路线、profile位置以及N05/N08所有门限不变。检验能否更早进入回中、保持定位健康完成释放后N05。

## 静态验证
41项profile tests和JSON/shell/结构/diff检查通过。下一步新冷启动，不在post-release/current-area N05与forward/start/terminal hold全部通过前执行目标。

证据：[静态报告](../../progress/evidence/n08-negative-y-rear-short-hold-profile-20261026-307.md)。
