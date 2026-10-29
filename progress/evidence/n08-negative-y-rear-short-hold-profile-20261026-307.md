# N08 后向短保持profile（#307 静态准备）

状态：profile/选择器静态验证通过；SITL未运行。

- 复制#306 rear-view profile，只将 yaw−π 的静止保持由12秒缩至4秒；转入rear、回到−π/2、回到yaw0和其余路线完全不变。全profile仍17阶段，比#306总时长减少8仿真秒。
- 唯一假设：#306在rear视角已到达后，回中阶段cost=1.0312只略过原门限；缩短rear dwell可在不改变运动目标和健康判据的情况下更早回中并完成N05释放检查。
- `python3 -m unittest tools.test_preflight_scan`：41项通过。JSON、`bash -n`、`python3 tools/project_status.py`和`git diff --check`通过；结构检查不替代SITL。所有N05/N08阈值保持。

SHA256：

- `config/components/simulation/preflight_scan.json` `b51748e5099f30c2e8663d504f0ebd083455d0adda9db19736e16a8b25ee9674`
- `tools/probe_preflight_scan.py` `5d9895582e5ebca008b8e1df80019fe544c79b33d252a7785521f3d5ceb20cce`
- `tools/run_n05_preflight_layout.sh` `c649ab11606a27bf20f99536b1b93b803ddfb1c9a977febf6801d3d2634116ab`
- `tools/test_preflight_scan.py` `edd46969d0b7e1f9786968d57953922aaa0ba11fcdf2296b08fca1b6f0163723`
