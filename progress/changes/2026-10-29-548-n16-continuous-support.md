# #548 N16 Goal开始与长时任务支持

Goal完成模式，用户范围N16全部出口；N15按#547排除，N11–N14已通过。核对真实runner最多3目标，新增显式continuous_navigation_min_sim_s：有限24目标上限、同一airborne/epoch session，达到所需仿真时间后完成当前目标再结束；不足时长显式失败，不靠静止保持。默认普通profile保持最多3目标。runner逐leg记录起始源时域，结束窗口/目标数/实际sim时长可审计。未改PX4/EGO参数或在线健康门。

文件tools/flight_profile.py、tools/run_vio_ego_flight.py、tools/test_flight_profile.py，源码修改前备份在artifacts/runs/n16-20261029-548-preparation。新增N16候选profile和协议draft，最多24次12m往返、600sim秒以上，无额外保持。往返/长期漂移尚未实际验证。

验证：PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=tools python3 -m unittest tools.test_flight_profile：5项PASS，含普通3目标限制、长时24有界、非法duration、600源时边界与时间倒退；py_compile、project_status、git diff --check。无飞行，不计N16通过。下一步多目标/连续源时间证据判断器和资源队列方法、隔离运行链与SITL验证。停止本子项完成，父Goal仍active。对话collaboration/dialogues/2026-10-29-548-n16-goal-start.md。
