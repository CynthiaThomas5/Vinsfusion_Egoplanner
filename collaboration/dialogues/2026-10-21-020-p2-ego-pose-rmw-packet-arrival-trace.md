# GOAL C EGO UDP packet arrival trace #354

- **任务摘要**：在 #353 已确认的EGO接收buffer profile下，观察最长pose take gap期间发往EGO participant UDP端口的数据报是否仍到达主机。
- **用户约束**：只做P0–P6单D435i仿真导航诊断；不改canonical源码、QoS、config或系统参数；不订阅truth／完整世界地图，不发布control。
- **决定**：复用run-local `listenSocketBufferSize=212992` profile和#353 reader probe库；ROS domain顺序复用220，Gazebo partition和VINS会话为新实例。临时Docker容器添加NET_RAW能力，仅运行 `tcpdump -i any -nn -tt -l -q "udp dst port 62427"`；输出只含时间、端点和UDP长度，无pcap或payload formatter。host直接抓包因没有CAP_NET_RAW被拒，未使用sudo。
- **结果**：最大take gap 2.484957 s。adapter发布48帧、独立reader收到48帧（最大源戳间隔66 ms），MapStatus epoch/map_id稳定；EGO 674次wait有673次unread=0、一次ready/unread=15。gap中packet tap记录2592条目的端口62427的数据报；首末记录覆盖空窗边缘，最大观测记录间隔25.367 ms。DataReader的1142次状态样本lost/rejected均0，449条listener事件均为data_available，gap末端两条unread=15。socket rb=425984，46次gap内ss采样的rx memory峰值465220 bytes，drop增加90。tcpdump全程丢弃7062个capture packet，精确到达率不可得。
- **结论边界**：packet tap可见同端口UDP流量，说明完全没有到达host capture point不足以解释空窗；无法确认数据报topic、是否由UDP socket成功取出或进入Fast DDS history。participant socket drop也没有topic/sample标记。GOAL C仍pending。
- **待决问题与下一步**：在不记录payload的前提下，对EGO receive syscall或Fast DDS receive路径计数，区分内核socket交付和reader history插入；随后继续vehicle-safe视角动作、多布局覆盖和轨迹执行。
- **证据**：[报告 #354](../../progress/evidence/p2-ego-pose-rmw-packet-arrival-trace-20261021-354.json)、[运行清单](../../artifacts/runs/p2-ego-pose-rmw-packet-arrival-trace-20261021-354/run-manifest.json)、[改动记录](../../progress/changes/2026-10-21-020-p2-ego-pose-rmw-packet-arrival-trace.md)。
