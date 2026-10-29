# #377 first-goal preflight addendum

状态：**已在发送首个目标前重新冻结**。SITL 容器已启动，但两次 ROS setup 均在 preflight 与飞行 runner 之前因 `bash -u` 下的未初始化环境变量退出；没有目标、使能服务或控制命令被发送。

- 独立 6 秒 PX4/bridge 读回：`DISABLED`、`landed=true`、`armed=false`、`control_enabled=false`、`vehicle_remained_disarmed=true`、`control_samples_zero=true`。原始读回：`artifacts/runs/n10-20261027-377-speed070-cancel-calibration/pre-driver-failure-readback.json`。
- 只修改 run-local 驱动器的 ROS/colcon setup 加载段：source 前临时关闭 nounset，加载完成后恢复；errexit 和 pipefail 保持启用。PX4 flight runner、ROS 包、planner、spawn、goal、取消速度窗与 runtime source/install SHA 均未修改。
- 驱动器 SHA-256：`cfde06e9d54d3f6711dabd106ed23aa79d73b557c2b8d99d19e727f5c1646cd4`。runtime source/install SHA 仍为 `b4707af345d1cd082dfb1cae3a24f24103134eedfce306205785b44342582ea7`。
- 原始 SITL 前 prelaunch 文件保留：[JSON](n10-cancel-stop-speed070-prelaunch-20261027-377.json)。此 addendum 是本容器首个目标前的有效 prelaunch 身份记录。
- 哈希：protocol `d08fe40d321c3f546efd0466b2e56dc450ce1804375a7663a0d1a71310348d96`；本 addendum `c448978bfb0602583ebdad2f2946cdcd93ef63ccfcf02532a563c9f39a891c24`。
