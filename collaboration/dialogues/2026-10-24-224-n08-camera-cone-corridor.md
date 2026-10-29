# 对话摘要：N08 #224 视场内走廊候选

- #222/#223 的额外左右 yaw scan 都在 normalized-cost 门限处 fail-closed，且没有 post-release map。没有放宽 health gate。
- 改用 #221 已通过的 exact same epoch/map 做离线目标筛选。起点 body sphere free，起点 hold sphere仍有41 unknown；目标路径必须重新按当前生产查询复核。
- 选定 `[+0.8,+0.3,0] m`：0.8544 m、偏光轴约19.01°，在水平 FOV87°内；target body/terminal hold及35个 continuous-line查询全部 free。纯 +Y0.4方向虽然地图free，但角度约88.46°超出视场，因此不用于飞行。
- 目标配置仅供 compute-only。#225 先 fresh N05与map gates，然后桥输入隔离计算／取消／hold／落地；当前不授权 XY，实际制动需经 same-run path/full-curve 与保守 stop boundary 验证。
