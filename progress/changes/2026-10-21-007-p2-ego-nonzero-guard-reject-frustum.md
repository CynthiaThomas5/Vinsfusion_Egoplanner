# 修改与验证记录

- 任务 ID／日期：GOAL C EGO 非零时刻 guard 拒绝点与深度视场配对 #332 / 2026-10-21。
- 对话摘要：[2026-10-21-007 对话摘要](../../collaboration/dialogues/2026-10-21-007-p2-ego-nonzero-guard-reject-frustum.md)。
- 修改文件：新增 run-local `artifacts/runs/p2-ego-full-spline-guard-nonzero-reject-snapshot-20261021-332/`，包含只读 observer、体素／相机视场分析、原始运行产物与 manifest；新增 [#332 轻量证据](../evidence/p2-ego-full-spline-guard-nonzero-reject-snapshot-20261021-332.json)、本记录和对话摘要；更新 GOAL C checklist、CURRENT、证据索引及 EGO patch 说明。没有改 planner、mapping、controller 或 canonical 依赖。
- 运行：复用 #328 planner binary、#330 场景／目标／运动 profile，以 ROS domain 187 和独立 Gazebo partition planner-only 运行 75.016 s。ready 地图状态下派发目标；425 次 full-spline guard 拒绝中 371 次在 t=0，54 次在非零时刻。首个非零拒绝在 `t=1.08 s`、`[0.390446,0.078722,0.454686]`。本轮未发 B-spline，EGO 有30条 odom/depth lost 警告；定位和地图在超时报告时仍为 valid/ready。
- 配对快照：首次请求因 `no_fresh_fused_depth` 拒绝，第二次请求在同 epoch/map_id 下成功，回调后约149 ms wall time返回；snapshot 的 depth source age 为114 ms。拒绝点 voxel `[123,120,6]` 为 unknown、raw-free、inflation=0；3×3×3邻域18 unknown/9 free，无occupied/inflated，known coverage0.638%。
- 视场结果：用 mapping helper 按 `0.15 s` 最大插值窗口计算深度源 stamp `26.170 s` 相机姿态。样点 optical 坐标为 `[0.203,-0.381,0.217] m`，在0.2–10 m深度裁剪范围内；投影像素约`(635,-351)`，超出640×480图像竖直范围。整格 `[123,120,6]` 均在该姿态竖直FOV之外。因此这次非零 unknown 拒绝可由未观测空间解释；它不是障碍证据，也不能视作安全空闲。
- 验证：#332 observer、voxel analyzer、frustum analyzer 的 Python 编译通过；两份 shell runner 的 `bash -n` 通过；Docker planner-only run 正常完成；offline snapshot/frustum analyzer 通过；run manifest、源码与全部引用产物 SHA-256 已校验。结构检查和 `git diff --check` 在文档更新后执行。
- 限制：只有一个 hypothetical candidate 样点与当前深度源视场对照；没有 B-spline、轨迹执行或未来姿态图像，30条输入超时警告未归因。在线 snapshot 不是独立真值；未知格继续按阻塞处理。没有 PX4、控制、真值、10分钟运行或实机证据，GOAL C/D/E/F仍未通过。
- 下一步：调查如何在不向 unknown 盲飞的前提下安全改变相机视角／机体姿态以观测垂直体积；新观测成为 known-free 后再规划，保留 epoch/map_id快照和全曲线检查。

未提交；保留工作树中已有用户修改，本轮无暂存或提交。
