# N11.1/#472 空场与图形界面准备

准备出口通过；正式飞行次数 0/3。本轮未发送 enable/arm/goal。

从 N10/#471 源码包构造独立候选，复用 #464 clean install/第三方依赖；仅场景删除19个圆柱，保留地板、房间与纹理。runtime contract 与 #470 比较只有 `simulation/worlds/ego.sdf` 不同，无新增运行文件。

按用户要求在远程桌面 :11 启动 Gazebo 与 RViz，X11 窗口列表确认两个窗口存在；RViz 日志报告 OpenGL 4.6。地面读回 bridge DISABLED/control_enabled=false/armed=false/landed=true，PX4 arming_state=1、failsafe=false；容器受控停止 exit0。

产物：[运行归档](../../artifacts/runs/n11-20261029-472-empty-gui/)、[场景准备清单](../../artifacts/n11-prepared/n11-20261029-472-empty-gui/scene-preparation.json)。归档包含 gui-windows.txt、ground-readback.txt、freeze-comparison.json、world.json、runtime-contract.json 和启动日志。

正式入口尚缺场景适用规则：冻结 acceptance 的 dynamic_replanning 和相关 observer 要求动态障碍注入报告，不能在空场直接满足；表面/分类指标也需要绑定空场墙壁/地板 ROI，而不是复用 #460 箱体。不得把缺失报告写成 PASS，现有数值阈值保持。

下一子项 N11.2：建立外部场景协议，明确空场无动态注入时的事件适用性；保留通用到达/VIO/地图时序/跟踪/全机净空/资源/身份指标，针对墙面准备几何与分类采集；运动和保持均需足够10秒RPE支持，保留全物理步与raw VINS速度。协议与判断入口完成后再冻结第1次正式冷启动输入。若需要修改冻结评估器，记录新身份并完成相应回归后计数。

停止原因：本轮有界准备子项完成；N11仍in_progress，正式0/3。
