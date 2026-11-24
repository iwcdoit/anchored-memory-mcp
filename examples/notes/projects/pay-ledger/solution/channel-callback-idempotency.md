---
title: 支付通道异步回调幂等设计
repository: pay-ledger
memory_type: solution
status: verified
commit: 9c2b5e4
code_paths: [pay-ledger-server/src/main/java/com/pay/ledger/callback/ChannelCallbackGuard.java]
code_symbols: [ChannelCallbackGuard#acquireIdempotentLock, CHANNEL_CALLBACK_GUARD]
tags: [idempotency, callback, state-machine]
---

# 支付通道异步回调幂等设计

`CHANNEL_CALLBACK_GUARD` 用于银联、网联及下游 POSP 通道异步通知的防重与状态机闭合控制。

## Observations

- [decision] 基于通道流水号与交易单号构建唯一幂等防重约束，结合订单有限状态机（仅允许从待支付跃迁至成功/失败终态）拦截并发重复回调。
- [verification] 模拟同一通道订单并发重放 10 次回调通知，仅首次触发终态事件驱动任务链，其余请求幂等返回成功。

## Playbook

- [probe] 只读核验通道回调幂等流水记录：`SELECT channel_seq_no, order_no, process_status FROM t_channel_callback_log WHERE order_no = :orderNo`
- [verify] 运行通道并发重复回调与状态机防重单测：`mvn -pl pay-ledger-server test -Dtest=ChannelCallbackGuardTest`

## Relations

- relates_to [[交易终态事件驱动编排规范]]
