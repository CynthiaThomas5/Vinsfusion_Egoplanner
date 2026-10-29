# N10.3/#439：同bag重力单变量回放

实际执行两个network-none离线VINS容器，仅g_norm9.80665/9.8不同。首次输入启动漏收不足保留，start-paused/发现publisher/Resume后两组完整输入和处理源戳均一致；结果未解决RPE/保持速度越线，在线参数/算法未改，无新飞行。

验证命令与源/输出指纹在artifacts/replays/n10-20261028-439-vins-gravity，脚本于artifacts/n10-prepared/n10-20261028-439-vins-gravity-replay，实际结果见../evidence/n10-vins-gravity-replay-20261028-439.md/json。py_compile通过。无控制会话需要收尾，两个回放容器已退出。该否定结论关闭#439研究子项，不关闭N10.3。

下一#440先隔离每图enqueue候选，保持g原值及其他参数，按同bag比较后再决定实施。对话：../../collaboration/dialogues/2026-10-28-439-n10-vins-gravity-replay.md。
