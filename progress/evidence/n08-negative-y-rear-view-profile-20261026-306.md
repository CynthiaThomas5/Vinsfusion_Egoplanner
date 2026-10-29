# N08 负 Y 后向视角 profile（#306 静态准备）

状态：静态profile验证通过；尚未运行SITL。

- 新profile `n08_overhead_free_sector_negative_y_rear_view` 从#305路线出发，保留前9阶段与路线；在home视角处分段转向 yaw−π/2，再 yaw−π，到后向后静止保持12s；随后经yaw−π/2、yaw0分段回中，再走原下降与落地支撑路线。
- 相较#305只增24仿真秒。来源是#305同身份raw map显示hold/sweep unknown集中于x≈−1.05m后向薄层，负Y侧视没有解决；#233也记录过后向起点hold unknown。
- 健康、unknown、map freshness、N05/N08空间、速度、跟踪和时间门限均未修改。mission仍只向前发EGO；此支架观察用于建图，不是返航航段。
- `python3 -m unittest tools.test_preflight_scan`：40项通过；新增测试验证后向turn/hold及分段回到yaw0。`bash -n`、JSON解析、`python3 tools/project_status.py`、`git diff --check`通过。结构检查不代表SITL通过。

SHA256：

- `config/components/simulation/preflight_scan.json` `46feb0f2733767d46e33f5580a96c85bac2566219b1523657ecfa5d032549a43`
- `tools/probe_preflight_scan.py` `b24e15cbd743451a0755af91ea0e3495a4ae9982f4f6f07e93ec3131b6cd1d70`
- `tools/run_n05_preflight_layout.sh` `e284f1a8b1373b2494b3ecb235b14d3af23b8514afed66184f17a1b205802f79`
- `tools/test_preflight_scan.py` `e9c31cbacad6fa45bf3c67730474f5c1b68704743398bc39f10689312974eec6`
