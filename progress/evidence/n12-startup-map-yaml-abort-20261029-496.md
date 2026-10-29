# #496 N12 目标前记录失败

独立GUI冷启动的preflight与takeoff admission通过，未发goal/enable。目标前ros2 topic echo输出包含丢失消息事件文本和tab，YAML解析失败，driver exit1；无flight.json及目标前launch record，不计正式飞行次数。N12仍1次正式飞行FAIL、0/3合格。

独立6秒直接PX4/bridge读回确认DISABLED、landed、disarmed、control disabled、零控制；全部ground safe checks通过，容器正常停止。原始污染YAML、driver traceback、独立ground readback及safe-to-stop均保存在[原始归档](../../artifacts/runs/n12-20261029-496-formal02/safe-to-stop.json)。

#497先核对Jazzy CLI支持--no-lost-messages，实际地面MapStatus使用该选项输出后正常解析且epoch一致。修复仅使这一条CLI输出保持YAML，不改变常规sensor capture的loss/error记录，不新增健康门、等待或拒飞分支。新外部release冻结后#498独立冷启动继续原驻留5s方案。
