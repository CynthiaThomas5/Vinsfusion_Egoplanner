# #557–#558 N16离线陀螺诊断与单变量否定结论

Goal完成模式。使用#555真实MCAP提取IMU、复用已审计的初始姿态gyro积分，得到0.035度最大yaw误差，与VIO2.91度差异有判别性。新增run-local同输入基线/gyro权重案例，完整native输入审计、原始固定PRESTREAM锚定姿态误差逐段比较，候选gyr_n0.001→0.0001无充分改善/角度略差，REJECT_NOT_DEPLOYED。未改任何生产配置/源码/参数，不启动飞行。

验证：两次离线实际进程EOF+drain完成、全部native输入fingerprint和立体处理完整；baseline重现实际末段误差，candidate保留失败；脚本py_compile、project_status、git diff --check。路径及指标见progress/evidence/n16-gyro-drift-analysis-20261029-557-558.md；来源/许可沿用#499/#515/#516的固定GPL来源与记录，不修改原实验/源目录。对话collaboration/dialogues/2026-10-29-558-n16-gyro-analysis.md。

下一步仅gyro已知零偏仿真校准约束的代码路径/数学一致性研究（保持accel偏置和其它参数），不要再盲目调整gyro权重或特征数量。真实正式失败不改，N16未完成，父Goal active。无活动离线/控制会话。
