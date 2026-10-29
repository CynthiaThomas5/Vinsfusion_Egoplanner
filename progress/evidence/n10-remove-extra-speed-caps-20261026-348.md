# #348 额外速度保护移除

用户明确授权后，当前导航runner移除了EGO参考/PX4实测速度超过0.12m/s触发取消的行为；速度改为只读观测，报告保留来源、采样数、峰值与最后样本。取消停车的EGO代码移除了总速0.10m/s及垂向0.01m/s的准入拒绝；有限有效状态仍是计算轨迹的条件。N10配置删除额外速度上限字段，活动planner配置仍为0.25m/s/axis、加速度0.25m/s²/axis，保留规划可行性约束。

验证：`bash tools/project.sh build ros`通过17包；`bash tools/project.sh test`通过407单测（含高于原速度门仍只记录、无效量测不伪造速度）及navigation-adapter/official-policy两项ROS集成。`python3 tools/fetch_dependencies.py --source ego_planner --target /tmp/d435i-n10-348-ego-replay`完成固定上游和全部补丁重放，整棵vendor源码逐文件一致。安装binary已含新有限值错误分支，旧取消速度拒绝错误字符串不存在。日志在`artifacts/runs/n10-20261026-348-remove-extra-speed-caps`，输入与日志SHA-256见同名JSON。

本轮无SITL飞行或实机。取消停车仍使用原低速数据派生的距离策略，移除速度拒绝不证明更高速的制动距离。旧N08/N09限定证据不扩展为新版本资格；N10继续in_progress。旧N08专项量测工具的试验协议仅保留历史身份，不进入当前official_ego普通导航入口。
