# #481 已批准的N11队列重校准

只读补丁0021独立vins构建通过；75项相关测试通过。固定输入回放1798条native记录通过，最大源滞后0.060s、等待特征0，原始队列统计保留。观察端29684IMU/左右各3598帧覆盖完整；生产BEST_EFFORT回调未做trace，不声称逐回调等价。

旧revision8哈希不变，#477新字段不足，旧FAIL不改。新revision9仍draft，正式0/3。下一#482带Gazebo/RViz的完整校准，之后才冻结、执行新正式次数。详见[JSON](n11-approved-native-work-20261029-481.json)。
