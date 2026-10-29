# #507 离线回放保存

关联[对话](../../collaboration/dialogues/2026-10-29-507-n12-offline-review.md)。

承接#506地图失败后单变量诊断：同一#506录包分别以8/16迭代进行隔离回放，未启动PX4/planner；两组player均正常结束并完成drain，输入观察各34924 IMU、左右4233图像，完整原生输入trace和输出已保存。实验计划artifacts/runs/n12-20261029-507-map-localization-review/experiment-plan.json。用户随后#508取消地图表面误差数值门，当前不以该已取消门为目标继续调参或部署16迭代。尚未据此证明地图分类根因或候选修复，生产保持8。
