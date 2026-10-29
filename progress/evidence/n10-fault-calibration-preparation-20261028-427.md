# N10.3/#427.1 故障校准准备

已恢复#426后续工作：确认#415容器已停止、无本项目活动飞行；选用#405-r02隔离depth-only断流协议，复用其runner/prelaunch到新的#427独立目录。唯一主要变量是#426故障处置实现。新运行身份 n10-20261028-427-fault-repair-depth-calibration。

已固定四个修复源码与三个观察器源码的SHA，详见 `artifacts/n10-prepared/n10-20261028-427-fault-repair-depth-calibration/preparation.json`。继承的prelaunch/tool-freeze依赖尚需逐项核对，不能直接把旧身份用于新校准。当前未启动SITL或注入；本项为准备产物，不构成校准通过。

下一子项#427.2：完成工具身份核对，按原3仿真秒depth-only断流执行一次校准，记录原始四元数故障（若发生）、LAND ACK/模式及独立终态。缺数据判不足；不新增CPU/统计值运行门。N15正式次数仍为冻结后。
