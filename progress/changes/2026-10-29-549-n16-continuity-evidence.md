# #549 N16独立连续性证据检查

Goal完成模式，用户范围N16全部出口。读取当前状态确认无项目活动仿真，恢复#548支持。新增tools/n16_continuity.py：独立从源时域窗口核对>=600sim秒、多个独立goal、同epoch帧、桥在整个窗口ACTIVE/armed/not-landed、独立真值覆盖、各leg实际匹配样条的READY命令及非零运动命令。旧短任务、拼接多次起飞、跨epoch、缺真值、错轨迹身份、纯零速保持不能据此通过。结果只属于连续性子项，必须另有实际运动/逐段独立到达/接触/资源证据，不能直接算N16通过。

验证：PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=tools python3 -m unittest tools.test_n16_continuity tools.test_flight_profile：12项PASS；py_compile、python3 tools/project_status.py、git diff --check通过。产物artifacts/runs/n16-20261029-549-continuity/tests.txt。无飞行，父N16保持in_progress。下一步资源/队列全时段覆盖及趋势方法、独立实际路径/逐目标到达/接触评估器、隔离运行链和GUI正式测试。不得将移除的0.2s/CPU峰值等门恢复为起飞或取消分支。对话collaboration/dialogues/2026-10-29-549-n16-continuity.md。
