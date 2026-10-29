# 对话摘要：N08 runtime profile fingerprint（#297）

- 高窗口取消 run #297 未发 goal/enable：旧 #276 build hash 将运行时 N08 goal JSON 与编译源码混比。新 runtime manifest 中的配置 hash 和当前配置相同，独立认证已经具备。
- N05 扫描 6/6、post-release online/offline准入和只读preflight通过；扫描工具 cleanup 警告后独立readback确认 bridge DISABLED、PX4 disarmed/landed、控制输出0。容器停止退出0。
- 修复：只将 goal profile 从 build-source equality 改为本次 runtime manifest equality；不是跳过 hash。runner/compiler checks 不放宽。
- 362 tests + navigation-adapter integration 通过。下一个新冷启动 run 为 #298，重新进行 0.07–0.09m/s motion-cancel。
