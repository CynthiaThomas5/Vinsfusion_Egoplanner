# N10.3/#440：隔离每帧候选

主源码/安装/参数不变；复制真实vins单包隔离构建通过，仅副本stride2→1。实际同bag候选回放结束，复用完整#439 baseline，公共源时间插值评估未改善原指标；candidate monitor少1条IMU，严格对比不足，未部署、不称因果退化。完整证据见../evidence/n10-vins-all-images-replay-20261028-440.md/json。

产物：artifacts/n10-prepared/n10-20261028-440-vins-all-images、artifacts/replays/n10-20261028-440-vins-all-images。真实构建/回放/源SHA/ldd和py_compile为验证；无SITL，不替代N10.5。当前实验子项完成，父Goal继续；下一#441依据实际solver迭代终止/时间余量，在原binary/stride/g下只将max_num_iterations8→16、max_solver_time0.04不变。

对话：../../collaboration/dialogues/2026-10-28-440-n10-vins-all-images.md。
