# GOAL C EGO Fast DDS receive-buffer差分诊断 #353

- **任务摘要**：对 #352 的socket drop / pose take gap做单变量诊断：只提高EGO participant UDP receive buffer，并确认profile确实生效，再在同一场景复测。
- **用户约束**：遵守本项目协作约定；只在P0–P6单D435i仿真导航范围诊断；不改canonical源码、QoS、config或系统参数；最终组合不订阅真值位姿／完整世界地图，不发布控制。
- **决定**：使用Fast DDS 2.14.6 participant profile，profile请求值212,992 bytes；仅EGO通过 `FASTRTPS_DEFAULT_PROFILES_FILE` 加载。mapping仍使用built-in UDPv4且不加载profile。EGO reader与adapter publisher QoS、场景和freshness gate均不变。一次使用错误环境变量的socket smoke作废后，以进程环境和host `ss`的 `skmem rb`重新验证；profile treatment的rb为425,984，profile-free同镜像／主机对照为212,992。未更改系统接收缓存sysctl。
- **结果**：domain 220中EGO最长pose successful-take gap为2.608148 s，期间adapter RMW publish 50条、独立reader收到50条且最大源戳间隔99 ms；MapStatus ready、epoch/map_id稳定。EGO 711次wait中710次not-ready/unread=0、一次ready/unread=25。listener仅有末段data_available(unread=8、25)，没有sample_lost/rejected回调；状态累计全程保持sample_lost/rejected=0。TID508/UDP62427的49个gap内host `ss`样本均确认rb=425,984、rx memory=0；gap内socket drop增加196，gap前后括区间增加202。提升接收buffer未消除take gap。
- **结论边界**：单次结果弱化“buffer大小本身”解释，不能定位丢包位置。socket级drop不对应具体topic或RTPS数据包；本run没有packet-level capture，不证明drop导致take gap。wait trace序号108–112缺失但位于目标gap外，全局连续性检查失败，选窗分析通过。Planner-only探针有2条未执行样条，无controller、trajectory server、PX4、truth或control。
- **待决问题**：gap内目标EGO UDP socket是否持续收到RTPS数据？如果仍有包到达，需继续区分socket接收与Fast DDS reader history；若没有，需检查上游网络／发送路径。下一步保留包头和时间戳、run-local地采集EGO端口到达事件，再回到vehicle-safe视角动作、多布局覆盖和轨迹执行验收。
- **证据**：[报告 #353](../../progress/evidence/p2-ego-pose-rmw-rx-buffer-trace-20261021-353.json)、[运行清单](../../artifacts/runs/p2-ego-pose-rmw-rx-buffer-trace-20261021-353/run-manifest.json)、[改动记录](../../progress/changes/2026-10-21-019-p2-ego-pose-rmw-recv-buffer-diagnostic.md)。
