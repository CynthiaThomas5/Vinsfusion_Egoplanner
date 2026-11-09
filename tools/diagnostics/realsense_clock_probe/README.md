# RealSense 同帧时钟诊断

仅用于独占相机的地面诊断，无ROS/飞控发布。main.cpp直接打开与canonical一致的五个流（640×480 IR1/IR2/Depth15Hz、gyro200、accel100），global time启用、emitter关闭；保存原值，正常/异常结束停止并关闭所属sensor，再恢复原选项。源配置改变时需重新核对，不能把此探针当运行相机配置副本。

trace_reader.cpp仅在此诊断进程通过LD_PRELOAD使用。它复制SDK的global_timestamp_reader::get_frame_timestamp原转换逻辑，记录同一次调用的原设备读数、原时域、转换结果、转换后system时间及ready。不更换生产SDK，不写原来源目录，不改变转换公式。仅允许与已核验布局的librealsense2.58.1基准一起使用，禁止注入VINS/相机生产进程。

来源：/home/jetson/realsense_debug/librealsense-v2.58.1/src/global_timestamp_reader.cpp，基准bf2778061d5dd29776e9aca8765f75852671760b，Apache-2.0，版权RealSense。生产库为既有HID hold/sensitivity构建，SHA256 a72cc3c5030be54ee532347d10a40b3839535bc79b2b4709d10d452c370b69f9。本文件复制的函数仅增加记录、等价局部变量及分支，无算法修复；版本/编译与验证状态见progress/evidence/hw103b-clock-20261104.md及对应run。不能将probe成功当导航/飞行资格。

构建用g++ -std=c++14 -O2 -pthread，main.cpp加SDK include/lib和rpath及-lrealsense2；trace_reader.cpp加-fPIC -shared、基准源根/第三方rsutils/include/既有build第三方json/include，与同一库链接。完整实测命令保存在本次run日志/变更记录。诊断结束必须确认sensor关闭、选项恢复和无进程占用。
