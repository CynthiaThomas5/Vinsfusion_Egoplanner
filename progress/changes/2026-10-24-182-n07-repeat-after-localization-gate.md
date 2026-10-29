# N07.28 #182：定位门失败后的新冷启动

## 执行模式与范围

Goal 完成模式；用户指定范围 N07。父目标保持 `in_progress`，#181失败后连续计数为0/3。继续同一固定版本的下一次独立冷启动，不改源码、配置、健康门、N05门限或地下边界规则。

## 已有基础与具体缺口

#180在2秒attached settle后完成N05 gates、30秒no-goal hover和独立评估，计1/3。#181初始attached只读gate接受，但后续显式settle后的重复gate因`localization_not_tracking`超时；fixture路线12/12后安全脱离，最终状态DISARMED/landed、fixture absent，无飞行。#181还暴露本轮marker读取字段错误和shell未fail-fast的操作偏差。当前缺口是取得一轮真正fresh且tracking有效的attached/post-release/current-area gate，并完成悬停。

## 单次执行流程与完成标准

- 新run/container/epoch；固定镜像、contract、spawn、layout、profile保持不变。
- 支架到ready marker后核对实际字段：`attachment=attached`、`vehicle_arming_state=1`、无真值输入且无控制/目标发布。
- shell启用`set -e`，ready marker后明确等待2秒，再运行一次attached N05 live gate及对应offline replay。若tracking或freshness失败，fail-closed、release并停止；不在同epoch重复检查以等待健康恢复。
- attached、post-release、current-area gates全都同epoch/map且fresh接受后，才开始no-goal hover。
- 30仿真秒悬停、独立位置和保持误差、PX4 EV/GNSS/ULog、ROS graph唯一控制publisher、有效tracking和时间域、最终landed/disarmed均按N07原出口核验。
- 成功后1/3；失败或失鲜按连续规则重置。保留支架helper的原始退出错误及独立安全readback。

## 当前状态

**结果：PASS；在 #181 失败重置后为连续合格冷启动 1/3。** Run目录：`artifacts/runs/n07-20261024-182-01/`。

固定镜像与runtime contract保持不变，新epoch为`ec1737eb9ab5458a8c2c750e6d592c1b`，map_id为`ec1737eb9ab5458a8c2c750e6d592c1b-532153ded6a84a4599af76d846d8e12d`。ready marker字段正确核对，attached且`vehicle_arming_state=1`，无真值/控制输入；明确等待2.000079941秒后仅执行一次attached gate。Attached、post-release、current-area online/offline gates全部`all_entry_phases_known_and_clear`，同epoch/map且fresh，N05 summary **14/14**通过。

支架helper错误原样保留：`fresh DISARMED status is required for every fixture command`，exit 1；记录同时显示12/12阶段、attached→detached、fixture removed、`fixture_may_remain_attached=false`、final landed。remove-service ack为false且helper safety_cleanup未完成；独立ROS/PX4/Gazebo readback确认bridge DISABLED、PX4 DISARMED/landed、fixture absent、LocalizationStatus valid且EV position/yaw fused。

无目标悬停 **30.0仿真秒**（33.334墙钟秒），未发送导航目标。flight PASS，定位状态667/667有效，PX4时间域254/254有效，无时钟回退；独立evaluator **11/11 PASS**，位置误差RMS/P95/max为0.005153/0.005931/0.006222m，绝对yaw误差RMS/P95/max为0.024213/0.032348/0.034448°。PX4 local hold最大位移0.071646m，Gazebo `d435i_link`真值最大位移0.072014m。N07未定义数值误差门限，这些值仅报告。

PX4 ULog **12/12 PASS**；54个空中estimator samples中EV pos/yaw/vel/height全样本active，GNSS/GPS aiding为0，最终PX4 disarmed/landed。ROS graph **3个只读快照**含空中快照，唯一bridge控制publisher与无truth ROS topic/node检查通过。末态bridge LANDED、armed=false、landed=true、EV有效。完整报告见[证据](../evidence/n07-no-goal-hover-20261024-182.md)和[结构化报告](../evidence/n07-no-goal-hover-20261024-182.json)。容器通过`bash tools/project.sh stop n07-20261024-182-01`停止并确认`Exited (0)`。

下一子项#183：同一固定版本的新cold start，保持正确marker读取和单次2秒settle gate流程；门限不变，成功后连续计数2/3。
