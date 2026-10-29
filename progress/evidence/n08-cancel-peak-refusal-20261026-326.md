# N08 #326：近峰值取消补测被 N05 安全门拒绝

**结果：** 按详细计划 D.6 的补充窗口 0.08–0.09 m/s 尝试 caller-cancel；没有发 goal、没有 enable 或起飞，因此不计为制动测量。#321 取消时实际 PX4 水平速度为 0.04014 m/s，未覆盖这个触发窗口。

N05 支架扫描六阶段完成、fixture 脱离且场景中无 fixture 模型。扫描后的 6 秒 bridge/PX4 读回为 `DISABLED`、disarmed、landed、控制采样为零。随后 40.001 秒只读 preflight 通过，最大 optimized-odom 回执间隔 0.11137 秒、overguard=0。附着阶段、释放后阶段和 mission current-area 的 fresh N05 online/offline 检查均在同一 epoch/map_id 上一致拒绝：`TAKEOFF_CONTACT:raw_unknown_in_expanded_vehicle_envelope`。因此 mission 在控制启用前 fail-closed；运行容器已安全退出，exit 0、无 OOM。

独立 raw-volume audit 找到接触包络内 51 个 unknown cell center，均落在拟合地面平面邻域；其中 37 个 odom x<0、14 个 x≥0。其余 ascent/descent 样本也各有 4/19 个拒绝，HOLD 区域则通过。在线报告没有 occupied hit；同图离线回放与在线一致。这个几何结果解释了 N05 拒绝，但不能单独证明未知区由相机后向盲区造成。阈值、代码和配置均未改变。

该记录不影响 #322/#324/#325 三次普通终点停车累计通过；也不覆盖或替代 #321 已通过的低速取消停止链。详细计划中的近峰值取消速度样本仍未取得有效飞行数据，需以后在 fresh N05 接触包络通过的区域重做。此样本不属于 `docs/remaining-small-goals.md` 的独立取消重复数或三次普通到达出口。

机器记录：[JSON](n08-cancel-peak-refusal-20261026-326.json)。Unknown-volume 审计：[JSON](n08-cancel-peak-n05-unknown-volume-20261026-326.json)。原始运行目录：`artifacts/runs/n08-cancel-peak-prescan-20261026-326/`。
