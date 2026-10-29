# N10.3/#441：迭代上限离线候选

实际回放完成且输入完整匹配，RPE略降但原两项仍未过，候选不部署。原始数据、在线配置、算法二进制和模型不变。另用真实MCAP做gyro-only积分核对，yaw误差远小于VINS；不把它当位置/飞行方案。

证据与验证见../evidence/n10-vins-iterations-replay-20261028-441.md/json；真实回放、完整指纹、公共网格及脚本py_compile，无新SITL。产物artifacts/replays/n10-20261028-441-vins-iterations16与对应n10-prepared目录。下一#442原配置中仅gyr_n降低一档，原阈值不改。对话：../../collaboration/dialogues/2026-10-28-441-n10-vins-iterations.md。
