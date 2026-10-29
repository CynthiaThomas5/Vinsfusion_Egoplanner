# N08 #313：低位后向观察 profile

状态：配置和静态 profile 检查通过；SITL 尚未运行。

## 试验假设

#248（20 s）、#307（8 s）和 #312（12 s）都在后向观察后下降时触发原定位健康门。#313 保留 #312 的前 10 个阶段、扫描各段时长和所有阈值，把 z=1→0.5→0 m 的支架回收段移到最后后向观察前；随后在 z=0、yaw=−π、pitch=−0.35 rad 作后向观察和 4 s 保持，最后在 z=0 回转到 yaw=0。假设将下降放在后向观察前可避免“后向观察之后下降”造成的代价累积，同时低位上仰视角能看到后方薄层。

配置共 17 阶段、总时长 462 仿真秒，和 #312 相同。D435i SDF 的水平视场为 87°；640×480 成像对应垂直视场约 70.88°。按模型相机相对 base_link 的 +0.12 m 前向、+0.08 m 高度近似，yaw=−π、pitch=−0.35 rad 时，x=−1.05 m、y=−0.25…0.45 m、z=0.85…1.15 m 薄层的投影角度约为垂直 17–29°、水平最大偏角 25°，落在相机视场内。该投影只用于选定观察姿态；是否被 raw map 正确观测仍由同身份 N08 几何门判定。

## 静态验证

- `PYTHONDONTWRITEBYTECODE=1 python3 -B -m unittest tools.test_preflight_scan`：44/44 passed。
- `python3 tools/project_status.py`：Structure/design PASS。
- `python3 -m json.tool config/components/simulation/preflight_scan.json`、`bash -n tools/run_n05_preflight_layout.sh`、`git diff --check`：通过。
- `validate_profile` 确认关节限位和 profile 可执行；回归测试确认 0–9 阶段不变、回收阶段前移、低位后向视角 pitch 与最终回中姿态正确。

## 下一步

冷启动 run `n08-cancel-highspeed-prescan-20261026-313`。只在完整扫描、夹具 detach/model absence/landed、同 identity post-release 与 mission-current-area N05 online/offline、40 s read-only preflight、N08 单向前向几何全部通过后，才执行 motion-cancel 单目标。任何门拒绝都不发 goal/enable；独立读回安全末态并停止本次容器。

机器摘要：[JSON](n08-low-rear-view-profile-20261026-313.json)。
