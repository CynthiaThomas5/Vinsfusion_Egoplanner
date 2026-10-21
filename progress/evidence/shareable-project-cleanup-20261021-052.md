# 可分享工程验证 #052

状态：工程整理完成；构建、133项回归、两次完整飞行及最终自动验收通过。逐项结果、失败记录和迁入脚本原路径／哈希／diff见[JSON报告](shareable-project-cleanup-20261021-052.json)。

原候选：[#051](cpu-navigation-convergence-20261021-051.md)保留，不能代替当前新构建。

本轮日志目录：`artifacts/maintenance/cleanup-20261021-052/`。保留初始Git状态、覆盖前备份、31项移出清单、所有失败尝试及重试日志。

- 源码核对：72个VINS／EGO关键源码与通过候选逐字节一致；之后仅VINS CMake增加0014运行包安装修复，不改变数值算法。
- 固定来源重建：VINS与EGO均从公开固定提交重放补丁成功；另一次独立VINS重放与规范来源全部文件一致，见`patch-replay.json`。
- 编译：`bash tools/project.sh build ros`重试16包完成，`bash tools/project.sh build px4`重试完成。日志`build-ros.log`、`build-px4.log`；原失败日志另存attempt1。
- 回归：`bash tools/project.sh test`，133项通过，见`tests-final.log`。包括fetch原子失败、补丁篡改拒绝、分享包排除项、运行指纹实际binary／配置变化检测、旋翼扫掠包络及角点变换，以及既有定位／规划／控制门控测试。
- 自维护模块核对：按原成功运行overlay顺序解析最终安装目录，21个Python模块与当前源码逐字节一致，见`own-runtime-equivalence.json`。
- SITL：`cleanup-room-01`未起飞，PX4编译目录默认值导致机架找不到；显式指定运行目录后使用新run继续，失败记录不覆盖。`cleanup-room-02`起飞并规划，在约4.84m处以`pose_stale`中止、`telemetry_stale`锁存并正常降落上锁；同参数`cleanup-room-03`完成导航与降落上锁，自动后处理因缺少matplotlib退出；将绘图改为可选并从SDF直接计算机体包络后，离线复算9项全通过。最小独立三维误差0.0923m，真实驻留3.171s，采样名义机体净空0.417m；全过程定位无效样本0、地图／导航失效行0。`cleanup-room-04`使用修正后的完整脚本自动完成，mission退出0，9项全通过；独立三维误差最小0.1010m，真实驻留2.649s，采样名义机体净空0.398m。两次成功运行源码／参数／binary指纹相同，全程定位无效和地图／导航失效均为0。失败试次均不计通过，尚不构成重建后三次连续成功收敛。

边界：当前房间单路线；未验证另一台机器完整冷安装、实机、完整连续机体扫掠、多场景或正式A–H。项目自有源码许可尚未指定；第三方许可证及世界来源声明随源码交付，不能把公开仓库或无许可声明等同于已获再分发授权。

分享验证：源码包试导出、解压后结构检查通过；完整交付在`artifacts/exports/d435i-project-20261021/`，含源码、固定镜像和SHA256SUMS。结构检查仅允许大历史artifacts链接缺失，其余源码／文档／里程碑证据链接仍严格检查。全部测试仿真在落地上锁后关闭。
