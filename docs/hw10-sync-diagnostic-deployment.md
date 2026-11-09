# HW10 同步边界诊断：部署与恢复协议（019准备，020已执行）

执行更新：020在用户明确授权后实读CRC匹配、诊断部署/未武装采集及原版恢复均完成，见[020证据](../progress/evidence/hw10-sync-20261105-020.md)。下文“尚未执行”保留019准备时状态；当前原版已恢复，后续101候选另行单变量验证。

范围：当前单飞控、未武装、仅EV诊断；保持10ms/2s/0.615998s门限、原1Hz/优先级和全部传感器/EKF，不进行真实控制/飞行。019本轮仅核验与准备，没有维护重启或刷写。下述操作须进入明确授权的维护/诊断范围后执行；不是自动部署脚本。

## 已就绪的具体对象

- 设备：新鲜USB system1/component1、FMUv5板卡50，V5006000，PX4 d6f12ad1c4f70ad3230afd7d86e971421e02fef4，GCC13.2.1 20231009，构建2026-05-13 18:50:48，stable/default。唯一设备由019 identity/USB记录识别。
- 原版来源：`https://px4-travis.s3.amazonaws.com/Firmware/stable/px4_fmu-v5_default.px4`，已固定保存为 `artifacts/runs/hw10-sync-20261105-019/official-stable-channel-px4_fmu-v5_default.px4`。
- 原版文件SHA256：`b50b275507da4cb0e218c943c2aff5359e3f0914c18f6b563494b925c0a0e403`；完整2064384B应用区的期望CRC为 **0x4f6ba085**。来源/嵌入构建信息匹配，**尚未与设备FlashCRC匹配**，不等于已验证回退。
- 候选：`artifacts/runs/hw10-sync-20261105-019/candidate-gcc13/HW10-SYNC-019-GCC13-DIAGNOSTIC-NOT-FLIGHT.px4`，GCC13.2.1、BUILD_URI `hw10-sync-019-gcc13-diagnostic-not-flight`。完整SHA/资源见[manifest](../dependencies/patches/px4/HW10_SYNC_BOUNDARY_GCC13_MANIFEST.json)。018的GCC10镜像不使用。
- 参数：019的`fresh-parameters.json/.params`公开1095项完整回读，与012/017原值零差异；910B SD BSON备份43项（37项CAL_）全部与当前值一致。MTD字符设备FTP取回0B，不能冒称已备份整片参数设备。
- 当前EV_CTRL/MAG_TYPE原0/0、SER_TEL1_BAUD1M、UXRCE_DDS_CFG101。SYS_AUTOSTART12001、CA_ROTOR_COUNT8、MAV_TYPE14是现有共轴八旋翼配置，**不自动改机型**；与实际机体一致性未验收，HW08控制/飞行门仍未通过。

## 019.2：先读取CRC，绝不能用上传器“代替验证”

1. 确认沿用用户已确认的拆桨、机体/相机固定、供电稳定；无本项目EV/控制进程，DDS未武装且输入publisher0，独占正确USB。读取新鲜system1/component1心跳并复用`require_unarmed_px4`校验，禁止凭历史状态操作。
2. 在已授权范围内，MAV_CMD_PREFLIGHT_REBOOT_SHUTDOWN(246) param1=3请求进入bootloader；重枚举后只绑定原设备，不用通配端口随便上传。该操作尚未执行，不把它当只读查询。
3. 仅在已进入bootloader后运行：

```bash
python3 tools/diagnostics/probe_px4_bootloader_crc.py \
  --port <该飞控bootloader端口> --already-in-bootloader \
  --firmware artifacts/runs/hw10-sync-20261105-019/official-stable-channel-px4_fmu-v5_default.px4 \
  --sha256 b50b275507da4cb0e218c943c2aff5359e3f0914c18f6b563494b925c0a0e403 \
  --output <新run>/original-bootloader-crc.json
```

该工具只发SYNC、GET_DEVICE、GET_CRC，要求已审查的协议3–5、board50、flash2064384B；不发重启、擦除、写入。错误协议/板卡/几何立即停止，CRC不匹配退出2。当前Flash的实际CRC不能在执行前填成期望值。

若CRC不同：不刷候选/原版、不抬门或强制覆盖；使用独立bootloader REBOOT返回仍未被擦除的当前应用，复核DDS/身份/参数并保存差异。此后要找到精确原镜像或另行决定基线变更。

**不要用 `px_uploader.py` 进行“只验证”**：当前上游CLI没有verify-only入口，`upload()`会执行erase/program。不得以identify/boot-check名称误触上传器。

## 020：仅CRC匹配且部署已授权时刷诊断候选

1. 核对候选完整SHA、板卡50和BOOTLOADER flash geometry。用019隔离checkout中的原PX4上传器，指定唯一端口和候选文件；不用`--force`、`--force-erase`、boot delay或bootloader更新。
2. 上传器应完成写入后的CRC校验并重启应用。确认`ver all`的BUILD_URI为019候选，不能只看相同git_hash；完整回读参数对比1095项，不重置/自动配置机型，不写校准。任何意外差异先停止诊断。
3. 首次先不加EV，确认原五类DDS、未武装/零输入、free/top/栈、同步trace的listener/短ULog、序号/flags/准确键都正常，保存原默认日志主题。019读取SD/etc为空，自定义logger_topics不存在；若现场后来改变，保留完整原主题，不用单trace文件替代。
4. 在同视角/两线程EV负载下，仅临时EV_CTRL11/MAG_TYPE6，显式近似bench EV；使用现有唯一EV桥接器，不创建Offboard/设定点/VehicleCommand发布者。新epoch，主测至少180s；保留定位锁定和尾部失流，不截断判通过。
5. 配合同轮Agent原生精确请求/回复时间与DDS记录，避免并发重负载回放；017显示计时也有开销，先确认采集负载。序号缺口、未配对请求、ULog dropout及观察器调度延迟必须保留。FC缓冲非空时的迟返与read→callback延迟作为内部路径证据；缓冲空的等待仍不唯一等于物理UART。没有新判别信息不继续重复采集。

## 恢复必须包含在同一次维护范围

- 结束EV/感知后恢复EV_CTRL/MAG_TYPE0/0并完整参数对照；保留用于安全收尾的监护，始终不武装。
- 保存完整ULog/同样本原始记录与哈希，停止本项目进程、恢复rmem和Agent原配置；不要清理无关服务。原版恢复前已用真实FlashCRC确认它等同原设备，是本协议的前置。
- 再进bootloader，按已授权恢复范围刷固定stable原版（同样禁止force/机型重置），完成上传CRC验证，启动后ver/1095项参数、CAL_、DDS五类、未武装/零输入复核。检查logger停止、.runtime空。
- 如候选启动失败，原应用不可用时按bootloader恢复通道写回已确认原版，不能强行用错误板卡镜像/抹校准。若硬件/端口/供电恢复条件消失，保留真实状态并停止扩展实验。

## 当前未通过项

设备实际FlashCRC、候选实机CPU/堆/栈/调度开销、真实FC/UART分界数据、017定位遥测锁定、HW08机体/控制资格，均未通过。本协议和构建通过不代替这些运行证据。
