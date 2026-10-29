# #255 输入回调一致性修复

对话：[摘要](../../collaboration/dialogues/2026-10-25-255-n08-callback-coherence.md)。

修改 localization node、health配置，增加20ms有限确认计时器；原健康门限与Health状态机保持。pending不输出／不刷新状态；逾期恢复禁止，质量故障立即锁存。新增只读未武装运行干预观察器。

验证与局限见[#254–#256证据](../evidence/n08-callback-coherence-20261025-255.md)。真实ROS方法测试6、相关回归71、17包构建均通过；未武装SITL消费者暂停可恢复、生产者断流仍锁存。未执行目标，不能视为制动测量或N08完成。下一项#257实曲线与同身份地图验证。

定向ROS回归保存在 `tools/ros_tests/test_localization_callback_coherence.py`，覆盖真实#254源戳、逾期恢复拒绝、持续断流、future、质量异常和pending状态不刷新；原始运行日志仍保留于artifacts。
