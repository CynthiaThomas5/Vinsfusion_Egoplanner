# 2026-11-02 实机只读调查

性质：环境盘点与历史记录核对，非实时传感器、构建、SITL或飞行PASS。

仓库基线dbb724f，初始`git status --short --branch`仅显示分支，工作树干净。检查了README、GOAL、CURRENT、milestones及实机路线，随后定向阅读localization、mapping、bridge、配置生成和launch代码。

SSH目标使用现有jetson别名对应主机。只读命令包括：

```text
uname -a
cat /etc/os-release /etc/nv_tegra_release
free -h
df -h /
ls /opt/ros
lsusb
lsusb -t
ls -l /dev/serial/by-id/
rs-enumerate-devices -s
docker --version
sudo -n docker images --format '{{.Repository}}:{{.Tag}} {{.Size}}'
fuser /dev/ttyACM0 /dev/video0 /dev/video2
```

结果：aarch64、Nano4GB、4.9.337-tegra、Ubuntu20.04.6、L4T32.7.6、Foxy；可用内存约2.5GiB、磁盘71GiB；D435I序列号243622073269/固件05.17.03.10/USB3 5000M；FMUv5.x USB串口指向ttyACM0；Docker26.1.3，sudo只读镜像列表为空。未观察到相机/VINS/ROS数据进程或上述被查设备的使用者，不据此宣称飞控未武装或所有串口空闲。

初次SSH被本地沙箱拒绝后，经工具权限升级成功。普通用户docker ps被socket权限拒绝，sudo -n只读images成功；没有修改docker权限。远端无rg，后续进程过滤改用grep。一次查询VINS源目录使用了不存在的VINS-Fusion路径，随后根据清单改为VINS-Fusion-ROS2，读得72023bc5d2abb14faa4c02a5c040d84f996b587a；无任何远端修复或变更。

读取的既有来源及边界：

| 来源（均在Jetson的~/realsense_debug下） | 确认内容 |
| --- | --- |
| environment_manifest.json | 旧SDK2.50/OpenMP清单对应035422071615，与当前相机不同 |
| ros_stereo_rgbd_imu_20261015_30s.json | 双目/深度约14.9Hz、IMU196.8Hz、单调性通过；深度16UC1；仅旧短时记录 |
| start_stereo_rgbd_imu_hid_sensitivity_global.sh | 当前相机候选入口，SDK2581-hid-hold-sensitivity，Foxy，双目640×480/15Hz，gyro200/accel100，unaligned depth |
| stereo_rgbd_imu_hid_sensitivity_global_params.yaml | global_time、linear_interpolation、emitter=0及IMU optical frame候选 |
| vins_integration/environment_manifest.json | VINS基准72023bc...、Ceres2.1/OpenCV4.2、旧静态600秒回归；dynamic accuracy=false，整体资格未通过 |
| vins_integration/CHECKED_INTERFACE.md | 仅实验接口，fresh finite仍WARN，failureDetection未启用，不具算法健康/飞行保证 |
| vins_integration/config/config_manifest.json及候选yaml | PROVISIONAL，optical IMU轴，td约−9.338ms，外参及噪声有明确未验证限制 |

相机wrapper基准在既有Foxy源码和HID-hold工作区均读得b30a25b400bddf28292058968fb69d96f9e1af9b；工作区补丁/二进制哈希仍应在真正迁入时重新锁定。本轮没有复制这些外部实现进仓库。

代码确认：SDF标定贯穿localization/mapping/bringup；bridge拒绝非gazebo_lockstep；launch写死sim time；VINS仿真开启known_zero_gyro_bias；mapping输入要求32FC1；health.json质量/时效只观察。上述为代码证据，不是实机缺陷复现。

结果用于[迁移方案](../../docs/hardware-migration-plan-20261102.md)。本轮未运行实时采集、串口协议请求、编译或飞行，无新会话需要取消/落地。PX4具体版本、真实外参、满载与动态精度仍未确认。
