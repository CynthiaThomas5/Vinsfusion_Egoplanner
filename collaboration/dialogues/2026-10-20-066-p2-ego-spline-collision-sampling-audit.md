# GOAL C B-spline 碰撞采样静态审计 #317

沿用 #316 保存的三个 B-spline、其控制点/knots 和近 start_time occupancy snapshot，逐一复现隔离 EGO 源码的自适应碰撞检查采样公式，再和既有 FSM 10 ms、前 2/3 安全窗比较。没有重建或运行 planner，也没有修改 `src/vendor/ego_planner`、canonical source manifest 或控制链。

轨迹 1/2/3 原优化器自适应步长约 0.189/0.189/0.337 s。根据配对 snapshot 回放，这组稀疏时刻均未落入 inflation mask；10 ms 网格在轨迹 2 的 1.15–1.24 s 找到10个膨胀样本，在轨迹3的1.20–1.25 s找到6个。两个曲线的检查范围内控制点都没有 inflation hit。这个静态结果重现了采样遗漏的候选机制。

限定：snapshot 在 spline 接收后请求，虽然其 header 与 start_time 相差0–1 ms，但不能证明 planner 优化时读到相同字节的地图；inflation 是轴对齐立方体，命中不等于真实物理碰撞。轨迹没有执行，也无真值净空或PX4证据。下一步仅在隔离源码中加密现有前2/3碰撞检查，并做构建与 planner-only验证。
