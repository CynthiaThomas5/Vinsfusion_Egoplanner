# #378 first-goal preflight addendum

状态：**已在首个目标前重新冻结**。#378 SITL 容器已启动；首次 run-local identity checker 因 `n09-runtime-contract-current.json` 尚未生成而在 preflight/飞行 runner 之前退出，没有发送目标或控制命令。

- 独立 6 秒 PX4/bridge 读回：`DISABLED`、`landed=true`、`armed=false`、`control_enabled=false`、`vehicle_remained_disarmed=true`、`control_samples_zero=true`。原始文件：`artifacts/runs/n10-20261027-378-speed060-cancel-calibration/pre-driver-failure-readback.json`。
- 驱动器已调整为先验证冻结的 `tools/runtime_manifest.py` 哈希，再生成当前 run manifest 并比对 runtime source/install SHA；实验变量、PX4 runner、planner、spawn、goal 与验收定义不变。
- 新 driver SHA-256 `4cb5b2515d42c97255a78b0e2834dbf6287fe8054a5a3c594a627e6d7ec3b155`；runtime source/install SHA `b4707af345d1cd082dfb1cae3a24f24103134eedfce306205785b44342582ea7`。原始 SITL 前 prelaunch 保留为 [JSON](n10-cancel-stop-speed060-prelaunch-20261027-378.json)，本 addendum 是本容器首目标前的有效身份记录。
- protocol SHA `ed94789c999dec92159ab2390a0197923b155fa59f22fbb1488dc23adb6b917d`；本 addendum SHA `aec1ebcc64001d00214db246fcc14f6f449b6720d28671f8432983809a412f9a`。
