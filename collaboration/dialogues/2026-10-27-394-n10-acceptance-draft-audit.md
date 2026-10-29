# N10.4/#394 Acceptance 草案与判断器审计

## 任务摘要

继续 N10.1–N10.7 Goal 完成模式。#393 已定量关联机体包络、跟踪误差与净空；本轮把该诊断、缺证据状态与综合采集合同接入单一 acceptance 草案，并审计离线判断器的身份与失败处理。

## 用户约束与实现决定

- Acceptance 保持离线评估器；CPU/队列/记录器/统计阈值不触发起飞拒绝、取消、暂停、降落或 disarm。
- 0.60 m 跟踪 P95、1.20 m sample max、0.10 m 全机净空等现有数值继续保持候选，不能删掉使报告变绿；无支持阈值的 tracking clearance 指标返回 `INSUFFICIENT`。
- Tracking report 必须匹配 runtime contract、run、goal、epoch、map 和输入 SHA。缺报、旧 schema、错身份或错输入为不足。
- 最顶层 identity 错误不能覆盖已经观察到的直接安全失败；分别报告 identity 不足和 FAIL。
- 采集合同要求完整左右目/IMU source/receipt 时间与图像诊断输入、同身份 raw/inflated snapshot、查询几何/半径回显、4 ms truth/接触、轨迹/重规划、资源/队列和 PX4 独立终态。仍在 draft revision 3，尚未冻结运行版本。

## 结果

- #381 acceptance replay：原目标驻留 FAIL、tracked budget INSUFFICIENT、身份/哈希匹配。
- #385 acceptance replay：到达 PASS，但全任务为 INSUFFICIENT；tracked budget INSUFFICIENT、身份/哈希匹配。
- #391 部分行重放：tracking budget 身份/输入匹配但无接受阈值；物理步 hold 净空归零、86 次禁止接触及紧急 closeout 保持 FAIL。
- 两组 targeted tool tests 26 项通过；Python compile 和 JSON 解析通过。无 SITL。

## 待办

N10.4 草案的判断器/不足态机制已验证，数值未冻结。下一子项是 N10.3/#395：补充综合运行只读图像/IMU 接收、地图查询响应和身份绑定工具，并验证缺采集时不会影响控制。之后才决定是否启动综合校准。
