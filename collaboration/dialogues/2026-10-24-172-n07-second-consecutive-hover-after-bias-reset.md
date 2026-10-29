# N07 #172：bias 越线后的新冷启动

## 用户约束

- 用户已授权Goal完成模式，范围N07，持续至N07出口通过。
- 保留原N05、定位健康和N07验收条件；不绕过raw unknown拒绝，不修改门限。
- 使用PX4 SITL，不发导航目标；只有N05释放gate通过后才运行no-goal hover。

## 当前证据

- #170完成当前固定profile和30秒no-goal hover，为独立通过样本，但随后#171失败，当前连续计数为0/3。
- #171启动期定位健康；支架第7段返回时`accel_bias_norm`越过0.15 m/s²并锁存，扫描7/12中止。原因尚未判定，安全清理与停机完成。

## 本项决定

#172仅改变独立冷启动epoch，沿用同版本和相同配置／流程，并用完整bias时序判断#171越线是否复现。重复出现则暂停悬停序列并转入证据驱动根因分析；不重复盲跑、不放宽健康门。

## 结果

#172在同一profile阶段7返程平移时复现`accel_bias_norm_exceeded`：首越0.15 m/s²于sim t=282.680，峰值0.179247。阶段6 pitch归零前后bias已由0.057167增至0.117803。与#171相同故障位置，#170及#167/#168同路线成功，说明存在跨epoch变化。安全拆架、移除、landed/disarmed和项目停机均确认；没有释放N05 gate或飞行。序列保持0/3。完整数据见`progress/evidence/n07-support-scan-health-failure-20261024-172.md`。

基于#166/#171/#172失败和#138/#148成功的route-level对比，下一步#173只改用既有`oblique_separated_return` profile，减少长时间0.45-rad斜视段；其余固定版本、wall layout、gate和健康界不变。当前相机安装坐标已在#142修复后，必须重新取得fresh release gate；若失败则不飞行。
