# #514 特征数候选否定结果

正式4线程环境下，完整同#512输入、原生callback和stereo处理均匹配bag。基线准确复现保持速度P95=0.012495m/s，max_cnt220→300后误差完全相同，候选不部署。源图像特征上限不是此录包误差的有效修复变量。初始64线程组保留但不外推正式环境。见[机器记录](n12-feature-budget-result-20261029-514.json)、artifacts/runs/n12-20261029-514-feature-budget/comparison.json。下一#515仅gyro权重比较，依据理想IMU与现录包独立gyro积分证据；原数值标准保持。
