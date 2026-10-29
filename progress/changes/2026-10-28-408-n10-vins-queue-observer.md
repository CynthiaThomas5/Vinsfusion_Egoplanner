# #408 N10 VINS 队列只读观测

新增 VINS 第三方增量补丁 0020，在既有 estimator telemetry 中输出 `accBuf`/`gyrBuf`/`featureBuf` 当前队列长度和进程期高水位。只读资源记录器按 localization epoch 订阅现有 telemetry，逐样本写 JSONL 并通过离线汇总明确处理缺失/异常值。队列仍无容量上限；没有新增 drop、拒绝或控制策略。

- 源码只在 `dependencies/patches/vins/` 保存变更；`dependencies/sources.json` 登记补丁顺序、patch/source SHA-256。
- 验证：补丁对当前锁定 0019 源码可应用且目标文件哈希匹配；`bash tools/project.sh build ros` 17 包完成，VINS 编译成功；ROS 镜像可导入资源记录器；汇总器 4 项单测、py_compile 通过；安装 binary 含 telemetry key。
- 产物：`progress/evidence/n10-vins-queue-observer-20261028-408.md/.json` 与 `artifacts/runs/n10-20261028-408-vins-queue-observer-prep/build-summary.json`。
- 局限：增量构建不是 N10.5 干净重建；尚无真实队列样本，需在下一次既有综合校准实测。该子项不单独起飞。
- 对话摘要：`collaboration/dialogues/2026-10-28-408-n10-vins-queue-observer.md`。
