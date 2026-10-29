# N08.2n #224：离线筛选视场内候选制动走廊

## 假设、变量与判据

- #221 的唯一被阻断候选是 +Y0.6 m 终端 hold sphere 有 16 unknown；start body、goal body 与 path middle sweep 已 free。额外 ±π/2 yaw 观察连续触发 normalized-cost lock，未取得 N05 post-release map。
- 假设缩短并朝相机光轴偏转的目标可以保留规定的车体／terminal-hold 几何门限，同时让完整制动路径落在 D435i 视场内。
- 只在 #221 exact epoch/map 上复用 production raw sphere 和 continuous-line 查询，遍历 0.1 m 平面候选；unknown 不填 free。选择不能替代新 run gate。

## 结果与产物

- 40 个网格点 body／endpoint hold／line 全 free，27 个也在 87°水平 FOV 内。
- 选择 `[+0.8,+0.3,0] m`：0.8544 m、方位 +19.01°；start/end body spheres 和 endpoint 0.980618 m hold sphere 均 free；35 个 continuous cover queries 全 free，cover radius 0.742824 m。
- Start body sphere free 但 start terminal-hold sphere仍有 41 unknown；本证书只适用于从已建立 hold 向前的候选路径，不宣称起点 hold 球全 free。#212 hold 与 N07 已通过结果复用，未复测。
- 纯 +Y0.4 m 的 map queries 虽通过，但 +88.46° 超出 87°水平 FOV，排除实际执行候选。
- 新增 compute-only profile [n08_compute_only_camera_cone_goal.json](../../config/components/navigation/n08_compute_only_camera_cone_goal.json)。完整离线结果见 [#224 报告](../evidence/n08-camera-cone-candidate-sweep-20261024-224.md)。

## 下一步

N08.2o #225 使用 #221 已完成的 15 阶段 `n08_overhead_free_sector_view` 及同一顶板＋box/column scene 建 fresh run；重新检查 current-area N05 online/offline、raw top occupancy、start/end body、full line 和 endpoint hold。均通过后运行 compute-only；未知、EGO 终止或取消／hold／landing 任一失败都保留失败，不执行 XY。
