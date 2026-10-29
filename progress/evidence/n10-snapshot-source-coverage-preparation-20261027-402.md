# N10.3/#402：地图快照源时间覆盖准备

## 归档复算

用 #398 的只读观测记录回放新的源时间覆盖判断器。快照触发时刻为 128.520 s；此前记录到 2 条正箱体 ROI cloud，最后一条 header/receipt 时间为 128.388 s，frame 一致，ROI 点数为 81。已有快照的融合深度源时间为 128.372 s，落后 watermark 0.016 s。

判断器将该快照分类为 waiting_for_fusion，should_retry=true。该复算确认新逻辑会抓住 #398 的 16 ms 覆盖缺口；它没有证明下一次飞行能及时得到覆盖快照。原 #398 地图分类结论仍为不足，且每十帧抽样一次的 ROI cloud 只能代表最新已记录观测，不能宣称覆盖所有 raw cloud 或所有融合输入。

## 准备内容

- 工具 tools/n10_snapshot_coverage.py 选择正 ROI cloud 的最新 header stamp，并校验 frame 和快照 source stamp。
- #402 observer 在首次快照请求时冻结 watermark，之后最多进行 5 次相同 epoch/map 身份的只读快照请求，间隔 0.25 仿真秒。
- source stamp 追上 watermark 才标记 covered；达到次数上限时仍保留被接受的数组，但标记 insufficient。
- 仅修改记录与离线证据完整性，没有加入起飞拒绝、目标取消、暂停或降落分支。
- #402 运行目录已准备，但尚未启动飞行，运行身份将在 prelaunch 阶段重新核对和冻结。

## 验证

命令 python3 -m unittest tools.test_n10_snapshot_coverage tools.test_n10_occupancy_snapshot tools.test_n10_acceptance tools.test_n10_sensor_capture 通过 45 项测试。#402 runtime-driver 的 bash -n 检查通过；Python 语法编译在临时 pycache 目录通过。校验对象和哈希见本报告配套 JSON。

下一项 N10.3/#403 聚焦可信的采样间净空下界。#398 已有连续 4 ms Gazebo solver-state 记录，但端点位姿差仍不构成区间最大运动界；需要基于有效动力学上界和机体包络推导、验证区间界。若物理假设不能从当前模型与源码可靠约束，保持 insufficient，并把确实需要的状态量测加入后续综合校准。
