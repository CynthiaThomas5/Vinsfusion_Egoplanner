# N08 #304 负侧短驻留 SITL 结果

- profile仅把负Y侧视到位后的额外驻留从18秒缩为8秒。
- 冷启动在第5姿态阶段期间cost=1.143026，超过原1.0门限；仅4/18阶段完成，尚未到侧视。初始N05因raw ground plane候选不足拒绝；无post-release map、目标或飞行。
- fixture removal、landed、安全读回和容器Exit(0)均有记录。
- 该轮不能判定8秒观察效果。#305拟复用#300已经完成且N05通过的路线，仅把其正Y观察窗口置换为负Y水平观察，避免把额外视角追加在长扫描末端。

证据：[运行报告](../../progress/evidence/n08-negative-side-short-dwell-prescan-refusal-20261026-304.md)。
