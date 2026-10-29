# N10.3/#448：原生回调证实首张左图缺失

隔离vendor副本增加只读receipt/processed_stereo/dropped_stereo trace；baseline真实构建47s，去配对帧catch-up discard候选也真实构建22s。原主vendor/install未改，副本来源commit72023bc5d2abb14faa4c02a5c040d84f996b587a、GPL-3.0及差异/源SHA已保存。

baseline离线运行到source约105.8s时已有直接判别信息（以下计数限定到两路外部监视器共同末戳105.736s，停止后的native排空后缀不混入比较）：外部RELIABLE监视器左/右各2967且都从7.868s开始；原生image0回调只有2966且首帧7.888s，原生image1有2967且首帧7.868s。原生处理立体帧从7.888s开始；paired-catchup drop trace为0。证实此处缺首左帧发生在原生订阅/回调接收之前，不能归因于尚未触发的配对discard循环。

据此提前受控停止纯离线Python回放（stop_reason=external_stop，子进程已收尾，未启动retained候选）；部分数据保留，不能用于完整任务指标通过。候选已构建但未运行/未部署，不作成功或失败结论。宿主首次SIGTERM因容器root所有权被拒，随后在对应容器内精确匹配Python argv后发送SIGTERM，正常生成部分报告并退出；无无人机控制/PX4/disarm。

下一#449只做离线原生传输资格：隔离copy将native IMU/stereo订阅BEST_EFFORT→RELIABLE，深度仍2000/5、原discard/stride/solver/参数不变，共享只读trace与可靠bag writer。不能直接部署到在线BEST_EFFORT传感器源；先验证真实原生接收及处理完整性，建立可解释基线。父N10.3仍未完成，原数值门限不变。

产物artifacts/n10-prepared/n10-20261028-448-vins-paired-frame-retention（源码diff、两个真实build、trace脚本）及artifacts/replays/n10-20261028-448-vins-paired-frame-retention（原生CSV、部分输出、external/native audit）。
