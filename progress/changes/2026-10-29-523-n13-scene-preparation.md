# #523 N13实际场景生成

Goal完成模式，范围为N13全部出口。新增tools/prepare_n13_world.py，从隔离N12合格候选复用半径0.5m、高3m圆柱，生成三处错位柱体，记录来源/输出哈希，断言非障碍模型字节结构保持；拒绝覆盖已有场景。产物artifacts/runs/n13-20261029-523-scene-preparation/ego.sdf及provenance，协议仍draft。源候选未修改，未启动飞行。

验证：生成脚本实际执行成功；Python语法、project_status、git diff --check见命令记录。结构/模型生成不代表SITL通过。未解项：逐障碍实际路线、地图与重规划执行判断器、场景绑定和三次正式冷启动。下一动作先完成判断器及负例，再部署隔离场景。
