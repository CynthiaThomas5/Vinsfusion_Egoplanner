# N10.3/#442：gyro噪声单变量离线结果

真实同bag、原binary回放，全部输入和源戳匹配；保持速度p95降到0.008798m/s，运动RPE10仍0.056415m未过原草案，整体不通过且未部署。主源码/安装/在线配置不变，只有隔离实验和证据文件。

验证为实际回放、完整指纹、公共源时间指标与脚本py_compile；详见../evidence/n10-vins-gyro-noise-replay-20261028-442.md/json。产物artifacts/replays/n10-20261028-442-vins-gyro-noise及对应n10-prepared。下一#443保持此离线候选gyr_n，只改acc_n0.01→0.001，原阈值/其他输入不变。对话：../../collaboration/dialogues/2026-10-28-442-n10-vins-gyro-noise.md。
