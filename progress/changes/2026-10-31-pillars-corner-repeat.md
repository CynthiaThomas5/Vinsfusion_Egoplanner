# 柱群跨场景航线重复实验

[对话](../../collaboration/dialogues/2026-10-31-pillars-corner-repeat.md)。无代码或参数变更。执行独立新会话 `./start.sh fly pillars`，run gui-20261031-014754-86595。与gui-20261031-012823-78682的runtime-contract sha256一致：True。

原生任务PASS、landed_and_disarmed=true；qualification FAIL，仅independent_arrival=false，其余六项true。联合位置≤0.3m/yaw≤15度驻留最长2.204sim秒，要求3秒；最小真实位置误差0.234332m。日志IMU重复时间戳观测保留。未改变验收阈值，不计完整通过。

原始产物：/tmp/d435i-vins-gui-standalone-20261030/artifacts/runs/gui-20261031-014754-86595
qualification.json SHA256：9f0e1a4cfcdbcaf7f2abb1b5b5637b1c665255ff943a4991744acc17c720a924

已落地上锁，GUI按用户查看要求保留。本次重复完成；未解项为终点联合驻留不足。
