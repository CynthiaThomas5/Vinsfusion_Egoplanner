# #209 N08.2a EGO 计算但 PX4 保持

## 任务上下文

继续用户指定的 N08 Goal 完成任务。N08 仍要求 hold／EGO 仅计算／EGO 执行对照、真实低速制动与至少三次独立冷启动目标重复。

## 决定与实施

通过 launch-only remap 让 EGO 保持向 `/position_cmd` 发曲线，同时仅将 bridge 对该话题的订阅 remap 到空的 `/n08/compute_only_position_cmd`。这样 bridge 按现有状态机继续 hold，不新增控制发布者；默认模式仍为原执行路径。run-local planner config 通过项目内相对路径传入，启动 manifest 记录其哈希，运行 mode JSON 记录选择。

## 验证与限制

17 包 ROS build、281 项工具测试、navigation adapter、Python／shell 语法、父子 launch 参数查询、结构检查与 diff check 均通过。本轮没有启动仿真／飞行／平移；没有证明运行期 ROS graph、hold 跟踪或取消停止行为。N08 未完成。下一步实现单目标 compute-only cancel runner，并保留当前平移动作禁行条件。
