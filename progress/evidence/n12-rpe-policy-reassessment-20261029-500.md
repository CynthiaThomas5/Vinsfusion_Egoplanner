# #500 用户取消5cm平移RPE门限，#498重新评估PASS

用户明确指令“把这个限制取消，然后继续”。当前N12起，10sim秒平移RPE P95不再设置0.05m否决条件，保留实测值和源时间支持；旋转RPE0.5°、绝对/速度误差、到达、地图、跟踪、机体净空、接触、资源及身份标准保持。新配置为config/acceptance_n12.json revision10，旧冻结配置/报告保留用于追溯。44项策略/历史兼容验收测试通过，未改控制分支、生产VINS参数或二进制；16迭代离线候选不部署。

#498本就是完整正式冷启动，runtime/goal请求与后续一致，旧报告仅平移RPE超限。新协议显式绑定原launch-record的SHA和原协议SHA，完整重算所有适用项；结果PASS且formal_count_eligible=true。平移RPE实测0.059407m仍显示为OBSERVED，无numeric threshold；独立到达4.248sim秒、单柱真实绕行、完整区间净空0.551996m、零违规接触、安全末态及其余指标均通过。不修改旧FAIL报告，不将校准算成正式次数。#494还有真实到达2.956s不足，仍保留FAIL。

N12现为1/3，需要另外两次独立可见GUI冷启动。当前运行组合保留8次迭代/原参数。产物：[新配置](../../config/acceptance_n12.json)、[新合同报告](../../artifacts/reanalysis/n12-20261029-498-user500-evaluation/n12-20261029-498-formal02/n12-scene-acceptance.json)、[冻结清单](../../artifacts/runs/n12-20261029-500-rpe-policy/release/freeze-inventory.json)。
