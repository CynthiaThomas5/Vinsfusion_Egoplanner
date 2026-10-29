# N10.3/#451：更低gyro noise通过保持速度项，运动RPE仍超线

相对449完整原生输入基线，只改gyr_n0.001→0.00001正数理想SITL floor；在线主码未改，binary/config其余参数不变。两案例native回调IMU39181、左右各4749，完整源戳SHA一致，4749对原始立体帧均被处理，无catch-up丢帧，队列保守HWM1。

hold速度误差p95从0.015166降为0.008090m/s，进入原0.01范围；运动10s平移RPE p95从0.060495降至0.057050m，仍超原0.05。完整原draft gate报告中唯一剩余FAIL是goal_motion RPE平移p95，其他已有数据项PASS。候选仅部分改善，不部署、不降低标准。

#438已证实当前world SDF重力9.8m/s²，VINS profile写9.80665；旧#439单变量仅改g_norm9.8，在当时外部monitor对比里误差变化仅微小，但现在native完整接收/处理协议已建立，适合重新验证物理输入一致性。下一#452只改g_norm9.80665→9.8，沿用449原binary/可靠native/trace输入协议和其余原配置/门限；不飞行、不故障校准。父N10.3未完成。

完整raw输出、配置指纹、native callbacks/processed timestamps、RPE及所有未改draft阈值见artifacts/replays/n10-20261028-451-vins-gyro-floor；脚本/命令见对应n10-prepared。
