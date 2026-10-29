# #587 终态记录原子写入与只读解析

范围：N17交付。#576飞行后flight.json写入时，独立地图观察器曾读到截断的JSON；原报错保留，所需地图/安全终态完整且冻结离线验收PASS。

改动：tools/atomic_record.py在同目录独占临时文件、完整序列化/fsync后os.replace，保留已有模式与正常umask；run_vio_ego_flight.py仅替换最后结果写入。record_n11_static_map.py对暂未完整的JSON继续只读等待。没有新增控制、拒飞、降落或数值门。

验证：PYTHONPATH=tools python3 -m unittest tools/test_atomic_record.py，2项通过；bash tools/project.sh test，734项单元测试及ROS集成通过，日志artifacts/runs/n17-20261030-587-evidence-io-fix/default-source-final-tests.log。

限定：最初在被矩阵切换为走廊的候选目录运行全量测试，4项默认房间断言失败；日志final-tests.log保留。随后在默认交付源码目录重跑PASS，无修改或放宽断言。#574矩阵控制/参数保持，#588验证修复后实际连续运行。

关联：N17用户授权代码整理/发布/迁移；对话摘要见collaboration/dialogues/2026-10-29-569-n17-delivery.md（若索引名称不同，以CURRENT中的#569证据为准）。
