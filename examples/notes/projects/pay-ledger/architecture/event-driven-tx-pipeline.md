---
title: 交易终态事件驱动编排规范
repository: pay-ledger
memory_type: architecture
status: verified
tags: [event-driven, pipeline, transaction, settlement]
---

# 交易终态事件驱动编排规范

`TX_TERMINAL_PIPELINE` 定义了支付通道明确返回终态（成功/失败）后的多链路任务编排约束，涵盖内部分账、后置计费、活动减免、营销减免与后置风控等 30+ 业务节点。

## Observations

- [decision] 强依赖节点（如先执行活动计费减免、再执行内部分账记账）归入同一任务链串行执行；无依赖链路（如后置风控与消息通知）并行调度。
- [verification] 新增后置业务节点只需注册对应终态处理器与依赖拓扑，主交易链路零侵入，单节点异常通过事务补偿隔离。

## Relations

- relates_to [[热点账户行锁超时排查]]
- relates_to [[支付通道异步回调幂等设计]]
