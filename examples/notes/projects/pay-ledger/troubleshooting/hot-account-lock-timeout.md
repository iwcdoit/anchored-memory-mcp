---
title: 热点账户行锁超时排查
repository: pay-ledger
memory_type: troubleshooting
status: verified
commit: 8f3a1c2
code_paths: [pay-ledger-server/src/main/java/com/pay/ledger/account/HotAccountShardingService.java]
code_symbols: [HotAccountShardingService#routeSubAccount, ERR_ACCOUNT_LOCK_TIMEOUT]
tags: [mysql, lock, sharding, ledger]
---

# 热点账户行锁超时排查

交易高峰期并发分账入账触发 `ERR_ACCOUNT_LOCK_TIMEOUT`（`CannotAcquireLockException` / `Lock wait timeout exceeded`）。定位原因为平台收益归集账户高频单行 `UPDATE` 导致 InnoDB 排他锁排队并阻塞数据库连接池。

## Observations

- [root_cause] 同一平台收益账户在高峰期承受集中并发写入，单行锁串行等待拖慢交易链路 RT 并占满连接池。
- [fix] 采用热点账户拆分策略，按峰值冗余拆分为多个子账户，通过订单号 Hash 取模路由分散写入压力，并配合定时任务异步汇总归集。
- [verification] 高峰期单点行锁等待告警清零，分账吞吐能力显著提升，日终子母账户总分核对一致。

## Playbook

- [probe] 检索近 15 分钟行锁超时日志：`error_code="ERR_ACCOUNT_LOCK_TIMEOUT" OR "Lock wait timeout exceeded"`
- [probe] 只读核查子账户分片入账分布：`SELECT sub_account_no, COUNT(*) AS tx_cnt FROM t_account_ledger WHERE parent_account_no = :accountNo AND created_at >= NOW() - INTERVAL 10 MINUTE GROUP BY sub_account_no`
- [verify] 运行热点子账户路由与定时归集一致性单测：`mvn -pl pay-ledger-server test -Dtest=HotAccountShardingServiceTest`

## Relations

- relates_to [[交易终态事件驱动编排规范]]
- relates_to [[支付通道异步回调幂等设计]]
