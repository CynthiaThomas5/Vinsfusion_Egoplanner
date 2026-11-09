# HW10-SYNC-018 FC同步边界诊断候选

[对话摘要](../../collaboration/dialogues/2026-11-05-018-fc-sync-boundary.md)，[证据](../evidence/hw10-sync-20261105-018.md)。

新增dependencies/patches/px4中两份非默认计时补丁、README与哈希/资源manifest；补丁分别针对实际PX4 d6f12ad1及Client711aef42，许可BSD-3-Clause/Apache-2.0。只在artifacts隔离clone构建，不改当前硬件、原来源或生产sources选择。原默认日志主题追加trace，不替换主题表。更新CURRENT/milestones及补丁索引，HW10仍in_progress。

验证：原版/最终候选完整px4_fmu-v5_default构建退出0；实际C++记录器/生成头断言、实际串口C/socketpair测试、补丁干净应用和逐字节比对通过；结构/py_compile/diff检查通过。最终Flash+1580B、SRAM1+448B，queue payload运行时另960B。CPU/堆/栈/实机/SITL未测，不把主机测试当真实调度。

本轮无设备运行会话或参数/镜像待恢复。停止原因：有界候选/离线验证完成；根因修复与HW10资格未完成。下一唯一项019核验回退镜像和诊断部署/未武装采集协议，不自动刷写。
