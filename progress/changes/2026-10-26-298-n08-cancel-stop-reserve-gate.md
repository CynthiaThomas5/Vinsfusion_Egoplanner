# 2026-10-26 #298 N08 取消制动包络触发门修正

- #298 新冷启动通过N05 6/6、post-release/current-area admission、40.01s preflight、0.6m路段和0.50m候选路段raw-map admission；高窗口试飞达到runner监测阶段。
- 运行时过严的点到原目标剩余距离门要求>=0.50m，挡住caller-cancel；未发布取消，也没有停止样条/制动测量。runner正常 operator-disable，landing/disarm成功；独立readback确认control0，容器Exit(0)。
- 移除该点到目标拒绝。0.50m仍参与motion-cancel的预先／空中raw-map走廊准入和独立测得停车路径长度评估；实时EGO exact replacement curve及terminal hold仍须fresh same-identity raw-map证书。
- 回归：`bash tools/project.sh test` 362项及navigation-adapter integration PASS。
- 证据：[运行报告](../evidence/n08-high-window-cancel-reserve-refusal-20261026-298.md)。
