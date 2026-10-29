# #304 N08 负侧短驻留前置拒绝

- 新 profile 将负Y侧视到位后的驻留从18秒改为8秒；SITL在第5阶段、抵达侧视前发生 `normalized_cost=1.1430264109` 健康拒绝，完成4/18阶段。
- 初始N05 online/offline一致拒绝raw occupied ground plane候选不足；无post-release gate／mission／goal／飞行。
- fixture移除与着陆得到确认；独立PX4读回bridge DISABLED、disarmed/landed、控制0；项目容器Exit(0)。
- 该run没有到达短驻留阶段，不能评价该变量。下一步#305基于#300已通过路线，将原正Y侧向窗口改为负Y水平观察，时长不变，检查缺失地图扇区。

证据：[报告](../evidence/n08-negative-side-short-dwell-prescan-refusal-20261026-304.md)、[JSON](../evidence/n08-negative-side-short-dwell-prescan-refusal-20261026-304.json)、[运行目录](../../artifacts/runs/n08-cancel-highspeed-prescan-20261026-304/)。
