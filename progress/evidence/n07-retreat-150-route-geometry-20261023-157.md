# #157 1.5m 后退扫描静态走廊

候选路线从 `spawn=-6.5m` 沿 x 轴后退 1.5m 至 `x=-8.0m`，保持 z=1m、yaw/pitch=0，再沿原路返回；起降垂直段也单独采样。静态 SDF 同时包含 wall/column N05 布局。按 N05 orientation-invariant reference radius 0.730618m、1cm 间距采样和 signed-distance Lipschitz 半步下界，四段均为正净空，最小连续下界为 1.189382m。

这只验证非地面静态几何。地面接触仍由 N05 fresh raw map 规则判断；支架、定位、地图准入、制动与飞行未由此证明。机器报告：[n07-retreat-150-route-geometry-20261023-157.json](n07-retreat-150-route-geometry-20261023-157.json)。
