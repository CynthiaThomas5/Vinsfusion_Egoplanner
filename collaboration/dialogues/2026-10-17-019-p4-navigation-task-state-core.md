# P4 导航任务状态核心

- 用户要求继续推进 GOAL；本轮承接真实 VINS 重启／新 epoch map reset 验收后，落实任务与轨迹失效规则。
- 约束：只改 `src/own` 自维护源码；保持 EGO vendor 源只读，第三方后续改动须用带基准和顺序的补丁；PX4 控制发布者只能是 `uav_px4_bridge`；结构或单测不能冒充运行闭环。
- 接口检查确认 EGO 当前使用 `/move_base_simple/goal`，其手动目标回调将 z 固定为1 m并忽略 yaw；现有 EGO 没有任务取消服务。故本轮先创建非空、可构建的 `uav_navigation` 任务状态核心，不假装 ROS action／EGO 清轨迹已经完成。
- 核心按有效 TRACKING 和目标 epoch 接纳任务；定位无效、epoch 改变或 ROS clock 回退时中止并发出 clear-trajectory 事件；支持目标取消／替换、旧轨迹拒绝、超时、位置+yaw容差驻留到达。
- 9项纯逻辑测试与 Jazzy 单包构建通过，摘要和哈希见 [P4 任务状态核心证据](../../progress/evidence/p4-navigation-task-core.json)。
- 待办：接 ROS action 与状态反馈，给 EGO 增加明确的目标 z/yaw 和取消接入，再对定位锁定、epoch 切换和 clock 回退做真实 ROS 集成验证；PX4 bridge 尚未实现。
