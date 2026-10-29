# N07 #196 对话摘要：第三次 cold start 在支架扫描阶段失败

## 用户约束

- 按用户“继续”恢复 Goal 完成模式，范围仍为 N07，直到该目标验收完成或出现真实阻塞。
- 保留原 N07 门限和 N05 准入条件；不得把地下空间解释成可飞区域。
- N05 全部正向准入门通过后才起飞；失败时安全收尾并记录，不伪报飞行通过。

## 本次执行

#196 起始 streak 2/3，但 N05 初始 online/offline gate 因 `TAKEOFF_CONTACT:raw_unknown_in_expanded_vehicle_envelope` 一致拒绝。未武装支架扫描在 7/12 阶段触发 VINS `normalized_cost_exceeded`（1.060107），helper 退出，未达到 online-check window；没有起飞。按三次连续验收规则 streak 重置为 0/3。

扫描 helper 已确认 detach、fixture 已移除、车辆 landed。首次 bridge topic echo 发生于 DDS publisher discovery 前；等待 discovery 后重复读回确认 bridge DISABLED、未 armed、landed，PX4 disarmed、land detector landed。容器 stop exit 0。详细报告：[N07 #196](../../progress/evidence/n07-preflight-health-failure-20261024-196.md)。

## 后续

#197 使用相同固定条件重新开始一次独立 cold start。先完成 N05 12/12 支架扫描、释放后的 fresh online/offline 准入和 summary 14/14；通过后再做 30 秒 no-goal hover、ULog、独立 evaluator、graph ownership 与最终落地上锁检查。地下空间不进入飞行区域。
