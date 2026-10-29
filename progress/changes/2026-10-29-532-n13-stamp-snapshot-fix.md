# #532 重复源戳与快照视图修复

改tools/debug_truth/evaluate_n13_route.py允许非降序，禁止同戳跨障碍平面插值；test_n13_route新增两例。prepare_n13_evaluation.py将快照目录copytree，保留hash及路径约束。实际归档全链复放errors=[]，独立路线三柱PASS，原始数据保持。证据progress/evidence/n13-formal01-route-reassessment-20261029-532.md。验证7项route单测、py_compile、project_status、git diff --check。

Goal模式，完成子修复并非N13完成。无活动仿真，未飞新任务。下一步修正版评估器发布/原launch身份明确重评，再推进两次正式冷启动。
