# #377 SITL prelaunch freeze

状态：运行前候选已冻结，当前尚未启动容器。

- runtime source/install SHA `b4707af345d1cd082dfb1cae3a24f24103134eedfce306205785b44342582ea7`（665 文件）；镜像候选沿用固定容器镜像。
- planner `config/components/mapping/n10_horizon5_speed080_calibration.json` / SHA `0f92519ded6f367387998f01e19a27e270b94c7571e12fbe5b80f82b8ed7473e`；spawn `config/components/simulation/n10_long_range_spawn_minus8.json` / SHA `b2534428e59c4b953e49f08a759b5cda8f1f0ea40f3a7d764923a797ff6f4aa2` / pose `[-8,0,0.3,0,0,0]`。
- 目标 profile SHA `0e275927089a9d04810d483fc6634717d6f7fcd15472a508601cbd5790600f00`；速度触发窗 `[0.70,0.80] m/s`。
- Run-local driver SHA `702e388d8d20e11ce0607351b28f26ae385681e1fe5e37d7e5c40de1598c0588`，基础 cancel runner SHA `7511b28c73a79d3b9fb4a857679e646f316a370b9b142059e73ef9d53ce4bac5`。先核对容器启动后实际加载的 planner、spawn、goal、contact overlay，再调用已有 cancellation runner；身份不匹配时不发目标。
- 禁止把项目自加健康门恢复；保留 PX4 原生检查。安全停止必须先由独立读回证明 landed/disarmed/control-disabled/zero-control。
