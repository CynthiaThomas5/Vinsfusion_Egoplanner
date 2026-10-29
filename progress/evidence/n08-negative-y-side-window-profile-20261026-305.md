# N08 负 Y 侧窗口替换 profile（#305 静态准备）

状态：静态profile验证通过；尚无运行资格。

- 新profile从 #300 已完成的 `n08_overhead_free_sector_view_profile` 复制整条路线，保持15阶段、全部阶段时长和行程不变。
- 仅把原正Y侧向观察两阶段（12 s与18 s，yaw=+π/2、pitch=−0.45）改为负Y水平观察（yaw=−π/2、pitch=0）；观察窗口时长、回中及后续下降不变。该方向对应 #300 的 fresh raw-map forward corridor中集中出现的负Y薄层unknown。
- `python3 -m unittest tools.test_preflight_scan`：39项通过；新增测试验证路线长度、时长和其它阶段不变。`bash -n`、JSON解析、`python3 tools/project_status.py`、`git diff --check`通过。结构检查仅表示结构一致。
- 下一步新冷启动支架扫描；post-release/current-area N05和N08方向／起点／终点保持证书全通过前，runner不会发goal或enable。

受影响文件SHA256：

- `config/components/simulation/preflight_scan.json` `a45219b25bd9c3579587359df42c6ad8e395fda79f80ffea3f58ee07c6e3cb3c`
- `tools/probe_preflight_scan.py` `06bff789f0b769f8dfa92e3fee1547a8a64f7a22f4f41d63f5c0161fc0d1f221`
- `tools/run_n05_preflight_layout.sh` `54020292c30ebcf25b1e8b7930f0147a0d591baa4668a2b19eca81ee5ad1c7f6`
- `tools/test_preflight_scan.py` `7f566a444fbc838059c395094218bd31e30294b48778ba5d74e8f60283709b95`
