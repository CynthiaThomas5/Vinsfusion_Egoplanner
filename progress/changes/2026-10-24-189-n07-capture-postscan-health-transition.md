# N07.35 #189：捕获释放后定位健康转换

## 执行模式与范围

Goal完成模式；用户指定范围N07，父目标保持`in_progress`、连续通过计数0/3。新冷启动；固定#188的镜像、runtime contract、spawn `-6.5,0,0.3,0,0,0`、wall layout、separated-return profile、hover参数和所有健康/N05门限。不修改运行代码或配置。

## 假设与单一诊断变量

假设：#188的 `telemetry_stale` 在全机支架完成后的释放/交接窗口由某个短时输入freshness越限触发；失效后再启动的12秒探针已无法观察触发瞬间。唯一诊断变量为探针开始时刻：#189在ready marker出现后立即启动只读 `probe_vio_stream_freshness.py`，持续至release后N05决定完成并额外观察2秒。用首次LocalizationStatus失效时刻与六路输入的源间隔、receipt age及clock age对照现有health policy，成功条件是定位保持或恢复合法tracking并取得完整N07出口；若仍锁存失效，则保存直接时间线并不飞。探针不发布消息、不改变门限。

## 执行流程与产物

新run目录 `artifacts/runs/n07-20261024-189-01/`。初始N05拒绝照常记录；ready marker后立即启动探针，随后按原流程等2秒并各运行一次attached online/offline check。附着检查接受后立即释放；确认fixture detached/model absent和独立PX4 DISARMED/landed后，优先执行post-release及current-area online/offline gates，避免先做耗时诊断。仅当所有N05 gates、freshness≤0.4秒及N05 summary 14/14满足，才运行既有30仿真秒no-goal hover和独立评估。任一健康或准入条件不满足都保持bridge禁用，不解锁。

探针产物：`n07-vio-stream-diagnostic.json`、`n07-vio-stream-events.jsonl`、`n07-vio-stream-probe.log`。N07 full-pass仍要求EV fusion、无GNSS/真值辅助、唯一控制publisher、30仿真秒悬停和最终landed/disarmed；连续计数只按新epoch结果更新。

## #189实际结果

新run `n07-20261024-189-01`完成12/12 support scan；attached、post-release和current-area三组N05 online/offline gates均接受且同epoch/map，N05 summary 14/14全true。helper仍以 `fresh DISARMED status is required for every fixture command` exit 1，但支架detached/removed得到确认。probe从ready marker启动，在current-area gate结束时被停止，窗口内定位持续valid至sim 480.992s。

随后无目标hover probe前置失败 `vio_bridge_map_preconditions_not_ready`。没有service call、takeoff、position command或goal；LocalizationStatus失效原因为 `propagated_stale`，bridge于sim 555.724先报 `external_odometry_stale`，PX4保持DISARMED/landed。由于freshness probe已结束，触发龄的源/receipt细节未采到。容器exit 0，N07保持0/3。证据见[报告](../evidence/n07-postscan-propagated-stale-20261024-189.md)。

## 下一子项

#190复用所有运行条件，把同一个只读probe持续到`flight.json`生成后，并在N05 14/14后立即启动既有hover探针，使释放后与hover前置连续覆盖；不更改健康门或其他配置。
