# 柱群起点累计左移5m与跨场景航线

[对话](../../collaboration/dialogues/2026-10-31-pillars-corner-route.md)。

修改pillars_spawn起点为world(-14,-9)，pillars_16m_goal（沿用旧文件名以兼容场景入口）相对位移(23,18,0)，约29.206m。终点world(9,9)，高度及终点yaw/到达门限保持；EGO地图X由40m扩至60m以覆盖相对X23m目标，Y40/Z6不变，vehicle_envelope关联配置哈希同步。RViz保持第三人称跟随。

先前gui-20261031-011843-67282及gui-20261031-012457-75709由用户改航线中止，均经唯一桥operator_disable正常降落上锁再停止，失败/中断产物保留。

最终执行./start.sh fly pillars，run gui-20261031-012823-78682。原生任务PASS/action_success=true/landed_and_disarmed=true；独立qualification FAIL：接触/正常终态/身份/唯一控制PASS，independent_arrival FAIL。联合位置≤0.3m且yaw≤15度的最长驻留2.908sim秒，要求3秒；最小位置误差0.23019m。保留结果，不降低门限。日志包含IMU重复时间戳观测。

原始产物：/tmp/d435i-vins-gui-standalone-20261030/artifacts/runs/gui-20261031-012823-78682
qualification SHA256：3ff791e87d3282719ca1a821840d05127c9a9ac2b24d32b07c8db4acaa1eae80

当前GUI已落地上锁，按用户查看需求保留。下一步：如需成功资格，再研究终点yaw/驻留跟踪原因；本轮位置修改与单次实验完成，不声称完整验收通过。
