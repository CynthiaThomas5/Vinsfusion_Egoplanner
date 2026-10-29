# N08 N05 接触面未知拒绝（#299）

状态：前置准入拒绝；没有发送 mission goal、enable 或产生飞行／制动测量。

## 结果

- 新冷启动使用 `n08_overhead_calibration`，N05 配置为 `n06_full_airframe_retreat_240_translation_only`。支架轨迹记录完成 6/6，模型已 detach/remove，epoch 与 map_id 在扫描前后不变。fixture helper 仍以 `fresh DISARMED status is required for every fixture command` 结束为 failed；该辅助错误如实保留，本次不标成完整的 N05 扫描成功。
- post-release fresh raw-map N05 拒绝 `TAKEOFF_CONTACT:raw_unknown_in_expanded_vehicle_envelope`，在线／离线结果相同。地面拟合有效，平面 z=−0.350 m，202 个 raw occupied 地面体素。
- 独立只读枚举发现 TAKEOFF_CONTACT 有 24 个 unique unknown voxel center，全部在 z=−0.35 m 平面；范围 x=[−0.35, 0.15] m、y=[−0.15, 0.35] m。ASCENT／DESCENT 各最多 23 个 unknown；HOLD 为 0。因 unknown 格位于拟合地面本身，接触区不能按“地下”规则排除。
- 4 秒独立读回显示 bridge `DISABLED`、PX4 未解锁且 landed、控制输出为 0；没有 goal/control 发布。项目容器已停止，exit code 0。

## 下一子项

#300 只改变 N05 支架扫描 profile，改用已有 `n08_overhead_free_sector_view`（包含俯视与侧向观测）来重新取得 ground-contact raw-map 证据；保持布局、机体包络、unknown 判据、N05 阈值和 N08 速度／制动门不变。该 profile 曾在 #225 同布局通过，也在 #242 的独立冷启动中途因定位质量门停止，因此本次结果仍需现场验证。只有新的 post-release 和 mission current-area N05 online/offline 均准入后，才启动取消制动 mission。

机器可读摘要、原始文件 SHA 与未知体素列表见此报告的 JSON；完整原始运行数据位于 `artifacts/runs/n08-cancel-highspeed-prescan-20261026-299/`。
