# HW10-SYNC-017 同样本分段定位

[用户决定摘要](../../collaboration/dialogues/2026-11-05-017-loaded-sync-segments.md)，[完整证据](../evidence/hw10-sync-20261105-017.md)。

未更改生产代码、固件或门限。运行时临时替换Agent加载路径至007计时库，原库未覆盖，结束删除/run override并恢复系统Agent。新建run-local采集/配对/CPU与源日志分析工件，原始数据在artifacts/runs/hw10-sync-20261105-017及-perception；更新CURRENT和milestones，HW10仍in_progress。

主测214.78s、211个精确配对，Agent中位0.141ms；6个高RTT中4个Agent占<2%，另2个3ms排队。CPU98.5%且内存约2.75GiB；214s后定位telemetry_receipt_stale锁定，原生solver日志0.654s停顿，连续融合未通过。选择下一子项为FC/UART边界计时方案/资源审查，不直接改优先级/频率/门限。计时附加负载、尾部丢失、USB回绕、ULog采样范围均在报告说明。

验证：persistent_session退出0、参数初末1095项零差异、ULog11145508字节下载；Python编译及CRC/完整尾URB/时间对齐断言、主测ULog覆盖/参数/未武装/终态无输入断言通过。结构检查和diff检查通过；无生产代码变更，无新增构建/SITL/飞行。收尾Agent65857 active/NRestarts0、桌面关闭、.runtime空、rmem212992、无临时overlay/usbmon、自有运行全停。

停止原因：有界诊断和恢复完成；功能修复及HW10资格未完成。下一项HW10-SYNC-018见CURRENT。
