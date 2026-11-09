# GS02 动态复测与Debian Codex状态

## 任务摘要

继续完成`docs/tasks/GS02-freeze-debian-migration.md`；用户说离开前先做不需要现场协助的工作，后补充Debian已安装Codex CLI，随后表示现在可以协助动态测试。

## 约束与决定

- 使用冻结ID `gs02-20261106-freeze01` 和Debian固定入口；动态测试只启纯perception/VINS、只读relay、RViz及记录器。
- 不启动EV/control，不武装/起飞，不改PX4固件、参数或同步门限；用户在安全地面条件下慢速移动并观察画面。
- Codex登录状态只读核验，不搬迁源机账户凭据。
- 旧run中的13.2–20.6秒reader滞后如本轮未复现，则记录为未定位、非复现历史观察；不宣称修复。

## 本轮结果

- Debian新动态run `hw10-groundstation-20261106T104050Z`，用户回报全过程无卡顿。5Hz窗口采样覆盖动态段，reader/定位/资源数据无长间隔；详见`progress/evidence/gs02-dynamic-rviz-20261107.md`。
- Debian Codex CLI版本`0.166.0`，`codex login status`显示ChatGPT登录有效；新ephemeral只读会话能够从冻结项目文件复述任务状态和边界，详见`progress/evidence/gs02-codex-context-20261107.md`。

## 待决事项

- 旧run的长reader滞后根因尚未唯一定位；本轮不据此修改生产链路。GS02任务按当前冻结版的迁移/动态展示出口完成，历史异常作为明确限制保留。
- HW10-EV-028、HW08安装资格与后续飞行验证仍是独立主线，不由GS02通过替代。
