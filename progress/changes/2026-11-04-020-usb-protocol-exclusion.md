# 单USB协议互斥修复（本地）

对应collaboration/dialogues/2026-11-04-020-usb-protocol-exclusion.md。范围沿用用户要求修复DDS，但本轮仅代码审查/受影响测试，不改FC参数。

修改tools/diagnostics/hw07_usb_session.py：DDS stop后status仍运行则exit1，禁止SYS2/MAVLink接管，保留hook。tools/test_hw10_boot_restore.py增加实际shell故障注入：DDS未退出时不得开始MAVLink或删hook。

python3 tools/test_hw10_boot_restore.py：3项通过；git diff --check通过。结构检查另执行。未部署到FC，不能宣称当前故障已修复。纯原始RX0意味着错误协议不是全部证据的唯一解释。下一步仍需读SD日志确认实际模块状态，禁止再次盲目切换。
