# N10.3 #367：动态障碍重试复测运行前冻结

状态：**工具已哈希冻结；SITL尚未启动。**

- runtime contract：`15d935eb803e76eb378aa4aa566d2d7b46b97168e2c75e7e0ee5d87878ed57a6`，665项输入。
- EGO binary：`25179a8ccdec7489c463f02e662180327bd34f90ef293ab1d0a0a85593d4982b`。
- patch 0053：`529fcade428165d4101cdc660b38f1cfd0094f22f0f77d03530e5808de7bb727`。
- ROS构建17包成功；日志哈希：`ad6631f7a7725e4a78d0f2eed195f08ea4ca6be78f656bfb8ebe4037fb575b0a`。
- protocol：`d6d320216385dc231631e20887a4b8c887710dc74a8d44b78ae7cdb411efd149`；注入器：`0647cc9f0dba53b8ca5d98a8e3bb7a595ff6df28ad5e559c52ecf4fa14f04cb8`；driver：`26a69a8f6b4295ffb2d27f776b406f2b9da57a79e64510c0f822167e55b6bf63`。
- 动态轨迹分析器：`686e410c49472dc6b5cf66490a776dd879a2bd0a9718eddedd4419ccc74d3453`；障碍净空离线评估器：`8b2b74b8dc3473ccde413e9d6d85f244600e9d3855fa6644e7a2f7abec946aaf`。
- 目标仍使用`config/components/navigation/n10_long_range_vio_calibration_goal.json`，spawn为`n10_long_range_spawn_minus8.json`，EGO profile为`n10_horizon5_speed080_calibration.json`。

飞行前 driver 将再次比对容器内 runtime hash，并等待 Gazebo create、action-cancel、map query、contact observer 和 bridge 状态服务就绪。任何身份或服务不符都在发 goal 前退出。机器记录：[JSON](n10-live-obstacle-replan-retry-prelaunch-20261027-367.json)。
