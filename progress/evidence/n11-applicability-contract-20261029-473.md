# N11.2a/#473 空场指标适用层与防误计数检查

本轮完成N11.2的有界子项：空场协议和离线覆盖检查。N11仍in_progress，正式0/3；完整采集/判断流水线尚未发布。本轮无新SITL或飞行。

## 实际改动

[协议](../../docs/protocols/n11-empty-scene.json)明确：N11为空场、保留地板和四面墙，唯一运行变化为冻结场景删除19柱；3次独立冷启动、GUI可见、完整落地上锁。冻结acceptance数值及文件未改，SHA仍为`7cf226ee4c471d49fec05f25eede1c9c127cd97fc22f0ae371ba13681d599750`。

动态障碍事件在空场协议中需有场景与无注入启动记录才可标NOT_APPLICABLE；原始FAIL及direct safety failure始终保留。该适用性只限N11；后续含动态事件的重规划验收仍保留。地图表面/分类继续必需，需本次墙面证据，不能用N10箱体数据代替。其余到达、VIO、地图时序、跟踪、整机净空、资源与身份指标保持必需。

[检查器](../../tools/n11_acceptance_contract.py)绑定冻结配置、冻结runtime参考、精确空场源SHA和实际生成世界provenance；核对启动记录/目标/epoch/map身份；拒绝超出场景的运行变化、重复指标覆盖失败、失配地图报告和缺失数据。协议仍为preparation，检查器禁止将此状态计入正式次数。该工具是根工作区新增离线评估源码，未复制进入已冻结飞行候选；后续使用独立评估器哈希绑定，不自动重写#471飞行身份。

候选协议目标为相对前向12m、上升0.1m、yaw0.2rad、native dwell4s、hold20s。目的为支持10s运动RPE和前墙观测；实际支持不足仍判不足，不把时长预测当测量结果。它尚不是已发布正式profile。

## 验证

`PYTHONPATH=tools python3 -m unittest tools/test_n11_acceptance_contract.py`：13/13通过，覆盖额外运行变更、动态/隐藏场景、provenance失配、配置篡改、缺飞行/地图、重复指标、动态FAIL及报告总FAIL保留、准备状态不可计数。测试使用合成输入，不是飞行证据。

实际归档回放：#472为INSUFFICIENT、formal_count_eligible=false；#460非空场为FAIL、formal_count_eligible=false。结果和测试日志位于[重分析目录](../../artifacts/reanalysis/n11-20261029-473-applicability/)。这是对误计数的反例验证，不是正式通过。

## 未完成与下一步

N11.2b仍需接通只读静态墙面raw/inflated快照采集、源戳覆盖、几何/分类评估及observer身份替换；N11.2c需完成全链路采集/判断预演再发布协议。数值门限不变，缺数据不新增起飞/取消/降落门。之后N11.3才执行带Gazebo/RViz的第1次正式冷启动。

停止原因：按普通单项模式完成本轮适用层子项；不关闭N11或N11.2父项。
