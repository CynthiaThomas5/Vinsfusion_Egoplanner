# #601 RViz俯视视角

- 用户问能否从高处向下用全局视角查看，随后要求调整。
- 决定：将RViz默认相机设为TopDownOrtho，中心约(8,0) odom、25m视野，匹配当前pillars场景和16m路线。
- 保留#596恢复的深色背景、青色observed history、inflated map层和颜色；只改视角。活动仿真保持运行，只重启RViz viewer以加载配置。
- 最终状态：俯视截图已验证，当前GUI保留供查看。
