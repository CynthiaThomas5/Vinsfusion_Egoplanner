# HW10-SYNC-019：回退核验与同工具链候选

[对话](../../collaboration/dialogues/2026-11-05-019-rollback-provenance.md)、[证据](../evidence/hw10-sync-20261105-019.md)、[部署恢复协议](../../docs/hw10-sync-diagnostic-deployment.md)。

新增只读bootloader CRC工具tools/diagnostics/probe_px4_bootloader_crc.py及4项测试，严格允许SYNC/GET_DEVICE/GET_CRC，绝不擦写/重启；未对实机bootloader执行。新增部署恢复协议；patch README改为指向019 GCC13候选，增加同工具链manifest，018原产物保留。两补丁不变，不进默认sources，不改当前飞控/Nano。

设备新鲜未武装，1095参数零差异，BSON43项/37CAL字段匹配；原版stable构建信息匹配但实际FlashCRC未读，期望CRC4f6ba085不冒称实读。GitHub release镜像时间不同而排除其精确回退用途。纠正018工具链10.3与设备13.2混杂，在019隔离clone同13.2完整构建基线/候选，Flash+1572B/SRAM1+448B，候选余38476B。工具链镜像包先与Arm官方SHA一致才执行，没有全局安装。

验证：只读身份/参数、源镜像校验、严格BSON、独立/上游CRC核对、4项主机测试、完整ARM构建、py_compile/结构/diff检查通过。设备CRC、恢复实测、候选CPU/栈/堆、时序与持续融合未测；MTD FTP返回0字节不算raw备份。所有工具链慢速下载已停、无EV会话，Agent/参数/运行配置保持。

019.1离线准备交付，019.2待明确维护授权，不标019回退或HW10通过。唯一下一项019.2维护重启/只读CRC；是否扩展到020诊断刷写与恢复由用户授权决定，不自动进行。
