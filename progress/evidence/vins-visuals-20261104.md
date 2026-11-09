# VIS11 实时VINS特征显示定向验证

本轮限定四类真实显示，完成；不更新HW08/HW10父状态。会话hardware-visuals-20261104-01，epoch167a9ce0d6b14266ad582ffa08889749。Nano ARM/Foxy perception + PC Humble RViz；无Agent/EV/控制、无飞控参数改变、无飞行。

## 真实观察

- verified-status.json：camera160包/2标记；points163包/末帧202点；history120包/末帧11点；image128包/1280×480；解码错误0；轨迹883点，vins_valid=true。不是空display占位。
- RViz截图rviz-verified.png：左侧真实双目特征跟踪，右侧白色当前点、绿色历史点、相机视锥/机体轴及轨迹，Global Status OK。历史来自margin_cloud，100秒保留，不是回环地图或稠密地图。
- localization-snapshot.log及health-summary.json：89.503s、88条健康观察，前4条为初始化，后84条均有效；优化约5.36Hz，流内记录最大优化接收源龄0.490s，末次健康观察源龄0.506s（含距上次消息的等待）。final-remote.txt进一步确认accepted_optimized887、TRACKING有效；本轮未出现健康锁定。
- relay采用原始sensor订阅先限频后反序列化，图像压缩、Marker按公共字段适配。CPU观察relay平均48.3%单核计、VINS143%、adapter104%、相机36.1%，表明新增显示有实际开销；这不是长期或规划满载资格。转发上限5/5/2/2Hz，实际可更低。

## 检查和复现

source /opt/ros/humble/setup.bash后运行python3 tools/test_vins_visual_transport.py、tools/test_hardware_live_view.py、tools/test_vins_config.py、tools/test_hardware_session.py均通过；py_compile四个受影响脚本通过。python3 tools/project_status.py结构PASS；git diff --check通过。15安装模块内容预检匹配；未修改编译包，无全量构建/SITL。本次实际启动同时验证Nano脚本可用。

入口与停机见docs/hardware-running.md。旧03正常停机恢复rmem后切换新session；show_track=1绑定新manifest。新relay PID364483且PGID相同，统一session接管；PC view13690/RViz13691，PID文件保存。按用户要求保留实时会话，活动rmem8388608；结束后须按CURRENT退出并确认恢复212992。活动日志会继续变化，证据快照/hash固定。

产物目录：artifacts/runs/hardware-visuals-20261104-01，sha256.json绑定健康摘要、状态快照、截图及最终远程观察。未解决：已知长时IMU未来戳、严格装机外参、HW10真实融合/控制资格；本轮成功不覆盖这些缺口。未启用回环/全局融合。
