# #588 最终连续回归：FAIL，安全收尾通过

运行n17-20261030-588-continuous，原始数据artifacts/runs/n17-20261030-588-continuous及-stack；派生评估artifacts/reanalysis/n17-20261030-588-continuous-evaluation/n17-20261030-588-continuous。协议原字节docs/history/n16-continuous-load-release588.json。

实际同epoch连续319.144仿真秒，6段原生到达；独立到达驻留依次3.628、2.444、3.952、2.420、3.976、2.464秒，返程三段均未达到3秒。冻结评估FAIL/independent_arrival_failed，不能算最终通过。其余来源/身份/完整性无不足；原始数据不改写。

独立safe-to-stop全部12项通过后容器正常停止。无新增故障专项。N16历史#566限定版本通过不改写，N17当前最终回归仍未通过。

下一次唯一主要变量：连续任务原生position_tolerance_m从0.25收紧为0.10m，保持native dwell5秒、离线0.30m/15度/3秒及其它参数；此为已有默认入口的native到达设定，不新增地图/健康/净空门。假设：native过早结束使VIO误差叠加后的真实位置进入0.30m区间过晚；判据为六段均独立达到3秒及其余完整条件。无新依据时不靠重复原配置碰运气。
