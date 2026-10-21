# 任务对话摘要

- 日期与任务 ID：2026-10-21 / 029
- 用户目标与明确约束：继续使用 ponytail 推进项目 GOAL；只做单 D435i 仿真诊断。不得把真值接入最终验收；不改实验来源；EGO planner-only，不发送目标或控制。
- 已确认的决定：#380 证明 receive API 是 `recvfrom`，原探针拿不到 ancillary counter；在 #381 的 run-local preload 中以内部 `recvmsg` 读取 `SO_RXQ_OVFL`，移除探针自己的控制消息后维持 `recvfrom` 调用方接口。
- 结果：synthetic 5000包压力测试通过。#381 运行中成功 take gap 2.560310 s，48条接收DATA记录均和 socket累计计数748–807配对。ACKNACK请求362/390/397；397于 gap 结束后2.62 μs到达接收API，计数807。socket总丢弃计数括号增长73，但不能逐序号归因。
- 待决问题：序号397的首次DATA未在EGO receive API中交付，是否由目标socket队列丢弃触发仍未证明；运行环境缺少CAP_BPF/CAP_PERFMON。
- 实施范围：只改run-local #381诊断文件及项目进度/证据文件；canonical源码、配置、QoS、buffer和freshness门不变。
- 对应改动记录：[P2 #380–#381](../../progress/changes/2026-10-21-029-p2-ego-fastdds-rxq-overflow-sequence-diagnostic.md)
