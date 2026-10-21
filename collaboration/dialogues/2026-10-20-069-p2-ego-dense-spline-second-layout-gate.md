# GOAL C 第二障碍布局快照门控诊断 #320

使用 patch 0029 的 #318 隔离binary，保持目标[2.5,1.4]、run-local参数和墙体不变，将箱体中心从[1.55,0.50,1.10]移至[1.55,0.90,1.10]，圆柱中心从[2.25,-0.50,1.00]移至[2.25,0.05,1.00]。目标前MapStatus ready，目标后探针收到2条 spline；没有 `final_spline_collision_reject`。两次只读快照请求都返回 `depth_pose_gate_closed`，因此本轮没有曲线/地图对照。EGO随后报告 depth lost 并进入EMERGENCY_STOP，未运行trajectory server或controller，也无PX4、truth、control topic。

决定：把#320保留为失败的快照门控尝试，不根据两条已发布spline推断净空。因为原进程停止后无法在原epoch继续取快照，我在新epoch重复同一障碍布局，使用可对瞬时门控拒绝短时重试的只读观察器；下一轮是新的运行和地图，不是#320原数据的延续。
