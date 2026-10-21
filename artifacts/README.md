# 本地实验产物

运行目录为 runs/<run_id>/，建议包含 manifest.json、logs/、bags/、maps/、metrics/、screenshots/。run_id 唯一，epoch 另存；原始数据不进入 Git。

manifest 至少记录软件版本及脏树快照、profile、配置哈希、起止时间、定位源、PX4 辅助源、epoch／map_id、命令、退出状态、原始文件哈希和 PROVISIONAL 项。run 保存后再在 progress/evidence 写轻量报告。不要把当前骨架检查保存成 SITL 运行。
