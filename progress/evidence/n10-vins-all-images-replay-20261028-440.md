# N10.3/#440：每帧估计器候选未获通过

> #447补充限制：此前完整输入校验来自外部监视器，不等同估计器原生实际接收/处理帧等价。相同配置已发现处理帧相位差异；参数结果保留为观察，严格因果修复支持待原生receipt/processed/drop记录。没有因此部署候选。


仅在artifacts内复制当前真实vins源码，MULTIPLE_THREAD的feature measurement enqueue stride2→1；g_norm9.80665、WINDOW_SIZE、相机/外参/求解参数和同bag固定。真实vins包Release隔离构建45s成功，编译flags/defines与原包一致；sourced ROS环境ldd无缺库。当前vendor和主install SHA均不变，没有注册或部署该实验补丁。

候选只在network-none容器离线回放，不运行PX4/planner；复用#439完整baseline，不重跑基线或飞行。对两组使用相同基线源时间点、同PRESTREAM参考和最大0.2s括号插值；原始位姿不改，避免输出频率翻倍改变p95解释。

| 项目 | 基线stride2 | 候选stride1 |
|---|---:|---:|
| 实际位姿样本 | 2364 | 4738 |
| 运动RPE10平移p95 m | 0.060494706 | 0.068600023 |
| 保持速度误差p95 m/s | 0.015166346 | 0.015834993 |
| 运动位置误差p95 m | 0.106709032 | 0.117092773 |

候选没有满足原草案指标。候选输入monitor还少记1条IMU（39180/39181），左右图完整4749/4749；因此严格对比资格不足，不称stride必然导致退化，也不为“证明更差”继续同类重放。记录保留，候选不部署。WINDOW_SIZE未变使时间窗缩短，这是频率变化的结果和解释限制，不能忽略。

新判别信息：baseline 2364个有效solve中1789个termination_type=1、1788个iterations=9（包括初始步、达到max_num_iterations8）；求解秒p50/p95/max=0.015534/0.026819/0.040252，feature queue高水位1。每帧候选对应solve4738、termination1=3573，feature高水位3。不是资源健康门，不据此拒飞。该数据支持下一单变量假设：在原0.04s时间预算下，将迭代上限8→16，检验未充分优化是否影响残余误差；回到原stride2和原g，不沿用未获通过的每帧候选。

实际产物：artifacts/n10-prepared/n10-20261028-440-vins-all-images（完整真实隔离源码/来源SHA/experimental delta/build/ldd/脚本）；artifacts/replays/n10-20261028-440-vins-all-images（实际输出、公共源点结果、solver-queue审计）。脚本py_compile通过，无新飞行，父N10.3未通过。下一#441离线迭代上限实验；输入monitor历史加大只为采集完整证据，不改算法输入或在线门限。
