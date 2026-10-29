# #511 只读起飞前查询合并

关联[对话](../../collaboration/dialogues/2026-10-29-511-n12-readonly-preflight.md)。#509源图像51–55s最大间隔0.036s，native gap0.332s且lag0.388s，异常53.164s在PRESTREAM55.74s之前。尚未唯一归因；本轮唯一变量是把重复ROS图查询/地图echo进程合并为一个只读rclpy participant，保留原endpoint计数、节点名、legacy输入和真实MapStatus读取检查。

新发布artifacts/runs/n12-20261029-511-preflight-reader/release，外部run.sh/prepare_run.py与新reader绑定SHA；源runtime/数值算法/参数/全部验收配置不变，完整会话仍评估，不删起飞前段。5项graph语义测试PASS。下一#512独立GUI正式任务验证，必须全指标过后才计第三次合格；若无改善，不称修复。
