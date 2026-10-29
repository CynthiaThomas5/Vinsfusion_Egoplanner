# #554–#556 N16首次真实长时任务与失败分析

Goal完成模式。隔离候选/home/huangxiaocheng/n16-20261029-554-continuous/project只改flight_profile.py/run_vio_ego_flight.py，新增N16目标profile及只读进程记录器，保留N14世界/生产二进制/运动参数。#554冻结300sim发布，#555 GUI真实任务325.212sim/6目标原生成功并独立安全停止；完整独立到达第4/6段FAIL，不计合格。

#556新增run-local Clock QoS适配补充观察器，控制链与原始空clock不改；新增tools/n16_process_lifecycle.py及4项回归，允许严格内核出生/结束后存活证明。evaluate_n16_run.py按该证据重评，进程项PASS，唯一实际FAIL仍为独立到达。发布旧sha和FAIL报告保留，未用故障注入或新在线健康门处理。详见progress/evidence/n16-formal01-failure-20261029-556.md及实际曲线。

验证：运行前27项、修复后31项测试PASS；GUI、完整任务、独立正常终态、实际全链及重评errors=[]；py_compile/project_status/git diff --check。当前无本项目活动会话。下一步定位IMU/视觉误差与yaw/往返的关系，证据支持后单变量修复再跑；原生容差约.01m而VIO漂移约.316m，不能靠收紧原生容差宣称已解决。Goal active，停止本轮安全会话已结束后分析交接，未完成父目标。
