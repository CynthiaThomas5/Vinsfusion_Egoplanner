# N10.3/#408 — VINS estimator queue 只读观测准备

日期：2026-10-28。针对 #406 暴露的 `accBuf`、`gyrBuf`、`featureBuf` 无界且没有运行高水位记录的问题，新增第三方补丁 `0020-readonly-estimator-queue-high-water.patch`，在既有 `estimator_telemetry` JSON 中记录三个队列的进程期高水位及每个处理图像帧前的当前长度。计数与快照使用已有 `mBuf` 锁；不设置容量、不丢弃/拒绝输入、不改变求解或控制行为。

资源观察器按 `/localization/status` 的 epoch 订阅对应 `/vins_raw/s_<epoch>/estimator_telemetry`，保留逐条队列样本到独立 JSONL，并离线汇总。缺失、格式错误或观测不单调都标记 `INSUFFICIENT`，不进入运行决策。高水位只描述实际观察到的积压，不能解释为容量或门限。观察器说明了处理线程停滞后可能没有新的图像帧遥测。

## 验证

- 基准为固定上游提交 `72023bc5d2abb14faa4c02a5c040d84f996b587a`，补丁在既有 0019 后应用；对当前 0019 源码 dry-run/应用结果哈希一致。
- `bash tools/project.sh build ros`：17 个 ROS 包完成，exit code 0；VINS 编译 41.7 s。仅报告原有 VLA 与 ROS `ConstPtr` 弃用警告。
- 安装的 `vins_node` 含 `queue_metrics` / `acc_high_water` 字符串；Build ID `f3897b96699011ceba322c7a9aec78602370149d`。
- 固定 ROS 镜像内可导入资源记录器，容量报告将 VINS estimator 队列标为源码无界；队列汇总 4 项单测通过，Python 编译通过。

构建与身份详情见 [`build-summary.json`](../../artifacts/runs/n10-20261028-408-vins-queue-observer-prep/build-summary.json)。本子项只完成观测实现和增量构建；没有实测队列值、没有干净重建、没有飞行。下一次既有综合校准需使用新 recorder hash，并将 18 个目标栅格前后状态和短时 depth ROI 同步记录。父 N10 保持 `in_progress`。
