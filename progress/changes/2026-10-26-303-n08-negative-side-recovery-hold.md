# #303 负侧视后增加 neutral recovery hold

## 修改

复制 #302 的 N05 observation profile，唯一增量是在 yaw 回中且 z=1.0m 后、原下降段之前加入 15s neutral hold。目的是在支架回收前重新采集水平图像并检查既有 localization health 门。未修改阈值或地图／运动安全参数。同步 probe 和 shell allowlist，并新增 profile 次序回归。

## 静态验证

`python3 -m unittest tools.test_preflight_scan` 37 passed；`python3 -m json.tool config/components/simulation/preflight_scan.json`、`bash -n tools/run_n05_preflight_layout.sh`、`python3 tools/project_status.py` Structure/design PASS、`git diff --check` 均通过。

SITL 仍待做。
