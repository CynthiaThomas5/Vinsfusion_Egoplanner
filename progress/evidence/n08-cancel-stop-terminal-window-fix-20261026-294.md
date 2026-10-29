# N08 #294：稳定性检查改为覆盖最近 50 ms 终端窗口

## 修复

#293 证明 EGO 以约 8 ms 周期持续发布 terminal `READY` 命令。原判据只检查最后相邻两条，并要求间隔至少 50 ms，因此在正常高频流下不断把终端参考视为未确认。

`terminal_reference_command()` 现在选取覆盖最近至少 50 ms 的命令窗口，要求窗口内每条命令的 goal、epoch、trajectory 匹配，flag 为 READY/COMPLETED，位置保持在既有 0.1 mm 稳定界内，速度和加速度为零。任一窗口内样本运动或状态异常都会拒绝该轮判定。PX4 实测 stop gate、3 秒保持、freshness、bridge ACTIVE/armed、source-time、map 和 landing 门均未调整。

## 验证

- 新增回归：8 ms 高频稳定终端窗口通过；窗口内存在运动命令时拒绝。
- `bash tools/project.sh test`：356 项通过，navigation-adapter integration 通过。
- 下一次冷启动 #294 重新做 N05、preflight、current-area admission 和 motion-cancel 实测；本次代码修复尚未获得运行资格。

#293 仍记录为 FAIL，成功次数不增加；N08 保持 `in_progress`。
