# #497 N12 MapStatus记录修复

N12 Goal继续。#496在goal/enable前因CLI loss-event文本污染YAML而停止；保留原始失败，不计正式飞行。独立ground DISABLED/disarmed/landed/control0确认后容器停止。使用本地ROS CLI支持的--no-lost-messages修复该条输出，真实MapStatus解析及epoch匹配验证通过。常规传感器观察器/数值标准/运行源码不变；#498以驻留5s方案继续。
