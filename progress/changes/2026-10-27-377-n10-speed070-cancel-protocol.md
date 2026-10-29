# N10.3/#377 high-speed caller-cancel protocol freeze

对话摘要：[2026-10-27-377](../../collaboration/dialogues/2026-10-27-377-n10-speed070-cancel-protocol.md)

## 本轮子项

依据 #376 当前 runtime 的 PX4 水平速度峰值 0.7418 m/s，冻结 #377 在相同 -8 m spawn、horizon5／0.8／0.25 `official_ego` profile 上，以 `[0.70,0.80] m/s` 水平窗触发 caller-cancel。#376 有 98 个有效速度样本落在该窗内。该窗仅选取接近实测峰值的制动样本，不是飞行限速、健康门或验收阈值。

## 产物与身份

- 协议：[Markdown](../evidence/n10-cancel-stop-speed070-protocol-20261027-377.md)、[JSON](../evidence/n10-cancel-stop-speed070-protocol-20261027-377.json)，SHA-256 `d08fe40d321c3f546efd0466b2e56dc450ce1804375a7663a0d1a71310348d96`。
- SITL prelaunch：[Markdown](../evidence/n10-cancel-stop-speed070-prelaunch-20261027-377.md)、[JSON](../evidence/n10-cancel-stop-speed070-prelaunch-20261027-377.json)，冻结前 SHA-256 `5183c2911a3a6aaeb841fbdc0e86784971cf58146d90515860ec3f0bd42d19fa`。
- Run-local identity-check driver：`artifacts/n10-prepared/n10-20261027-377-speed070-cancel-calibration/n10-runtime-driver.sh`，SHA-256 `702e388d8d20e11ce0607351b28f26ae385681e1fe5e37d7e5c40de1598c0588`。启动后核对 runtime 指纹、有效 planner 路径/参数、spawn 来源/hash/pose、goal 和 contact overlay，再调用既有量测 runner。
- 无产品源码、参数、验收阈值或碰撞规则变化。

## 有效量测定义

真实触发速度位于冻结窗、caller cancel 被确认、出现替代 EGO trajectory、PX4 水平速度 ≤0.03 m/s 且垂直绝对值 ≤0.05 m/s 持续 1 仿真秒、PX4 样本最大间隔 ≤0.20 s、真值空档 ≤0.04 s、contact observer 完整且无违规接触；独立终态读回必须为 landed/disarmed/control-disabled/zero-control。否则保留失败或不可判定记录，不改门限补救。

## 启动前检查

`bash -n artifacts/n10-prepared/n10-20261027-377-speed070-cancel-calibration/n10-runtime-driver.sh` 通过；协议、prelaunch 和工具 SHA 互相核对通过。SITL 尚未启动，后续先用固定环境变量启动，再由 run-local driver 验证实际加载身份。
