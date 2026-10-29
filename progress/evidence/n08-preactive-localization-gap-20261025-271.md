#271：起飞未到 ACTIVE，定位状态回执空窗触发安全退出

## 已通过的前置条件

新 cold start 使用 `config/components/mapping/n08_low_speed_trial.json`（max velocity 0.10 m/s、max acceleration 0.25 m/s²），launch manifest 路径正确，配置 SHA-256 为 `f8216372bdeda44f02b891381adbdb806c8866f252698dda87c29d14a6e29cce`。N05 支架扫描完成 15/15；工具仍记录 `localization changed or became invalid during physical scan` 泛化警告，但释放后与 mission current-area 在线／离线准入均接受，同一 epoch/map_id。40.00149 s 只读 preflight 通过，optimized odometry 最大回执间隔 0.11583 s、超过 guard 计数为 0。mission 前 raw-map 前向 capsule 和 home-pad entry 也通过。

## 起飞阶段结果

Offboard enable 被接受，bridge 进入 TAKEOFF，PX4 记录外部解锁和 takeoff detected。bridge 没进入 ACTIVE。runner 的 `localization_tracking_fresh` 使用既有 0.2 s 状态新鲜度门；记录到一处 0.344954 s 的 `/localization/status` 回执间隔，前后样本均为 valid TRACKING，整个记录 906 个样本均为 valid TRACKING。该间隔是 runner 在 ACTIVE 前中止的首要解释，但现有记录没有证明造成回调空窗的根因。runner 以 `trial_takeoff_did_not_reach_active` 结束并请求降落。没有发送 EGO goal；`takeoff_settle` 未记录，新增垂直沉稳门未被测到。独立 evaluator 因无 goal 时间戳缺少测量输入，因此没有新的制动数据。

## 安全末态与局限

记录中的末态为 bridge LANDED、armed=false、landed=true；PX4 最后状态为 disarmed，PX4 log 包含 `Landing detected` 与 `Disarmed by landing`。运行后 project stop 退出 0、容器已退出。安全归档由运行报告与 PX4 log 整理，明确标为归档而非 live ROS 快照。

## 下一步

#272 只移动 N08 未使用的 `/grid_map/occupancy` 观察订阅关闭时点：raw snapshot、capsule 和 home-pad 证书通过后、Offboard enable 前关闭。通过比较状态回执最大间隔和是否到达 ACTIVE 检查该负载假设；保持 0.2 s freshness gate、N05、速度、unknown、5 cm 曲线管道、tracking margin 与 vector cap 不变。

原始记录：`artifacts/runs/n08-20261025-271-vertical-settle-correct-profile/`；结构化摘要：[`n08-preactive-localization-gap-20261025-271.json`](n08-preactive-localization-gap-20261025-271.json)。
