# #520 N13策略修改与源码核对证据

本轮为配置/离线评估策略修改与源码审计，不是N13正式飞行通过证据。用户取消机体最小净空0.1m数值否决，新增revision12及5处比较移除；其它数值、零碰撞、数据完整性保留。历史N12冻结配置/结果及其源代码字节身份已核对，未覆盖。

验证：69项新旧策略单测PASS；py_compile通过；归档#501仅作新策略输入复放，跟踪/全机项支持新规则，整体仍INSUFFICIENT，未计N13次数。结构与diff检查记录见artifacts/runs/n13-20261029-520-clearance-policy/checks.log。

产物：[完整限制清单](../../docs/n13-project-restrictions.md)、[N13配置](../../config/acceptance_n13.json)、[机器记录](../../artifacts/runs/n13-20261029-520-clearance-policy/restriction-inventory.json)。N13场景/协议未冻结，无飞行启动，下一项为N13准备。
