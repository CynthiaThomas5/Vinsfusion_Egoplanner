# P0 固定容器归档导入与启动复核 #285

## 用户约束与决定

- 继续完成根目录`GOAL.md`，遵守项目AGENTS；不回滚或暂存工作区已有修改，不触碰旧PX4/ROS来源。
- 使用项目固定镜像归档，不以其他tag或联网临时镜像替代；区分归档导入、包/CLI启动、工作区构建、SITL和飞行证据。

## 已确认结果

- `SHA256SUMS`全部匹配且`zstd -t`通过。
- 本机Docker daemon中原本没有项目指定的基础镜像和VINS派生镜像标签；载入归档后两者image ID与固定清单一致。
- `d435i-vins:dev`容器启动成功，`libceres-dev`版本为`2.2.0+dfsg-4.1ubuntu2`，ROS Jazzy CLI可启动。
- 这次没有检查daemon是否存在其他无关镜像，因此不宣称完全空daemon导入验收通过。也未做colcon/SITL/PX4/飞行验证。

## 待办

- 完全空Docker daemon导入仍可单独验证；镜像启动本身不替代GOAL中的其他构建、实时仿真和导航验收。