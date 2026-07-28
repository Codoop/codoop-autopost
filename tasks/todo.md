# 内容发现与生产解耦 TODO

> 对应详细说明：`tasks/plan.md`

## 实施前

- [x] 确认 `tasks/plan.md`
- [x] 确认 alpha 阶段可接受“新工单只能来自 lead”的破坏性升级
- [x] 保持 `skills/_shared/agents/marketing-twitter-engager.md` 原文不变

## 任务 1：文件状态机

- [x] 为发现运行和 lead 增加本地文件读写
- [x] 建立 `available/claimed/consumed/rejected/runs` 目录约定
- [x] 实现相同规范化 URL 更新而不重复建 lead
- [x] 实现原子领取、恢复、拒绝和消费
- [x] 增加状态机测试并通过检查点

## 任务 2：发现 Skill

- [x] 新建 `codoop-content-discovery`
- [x] 每次只选择一个发现方向并轮换
- [x] 用 fresh Twitter Engager subagent 审核全部新候选
- [x] 保存完整 `value-review.md`
- [x] 仅把 `go` 候选加入 available
- [x] 覆盖普通价值、爆发趋势、无 go 和 AISI 行为测试

## 任务 3：线索池驱动工单

- [x] 内容生产自动选择并领取未过时 lead
- [x] 移除任意 topic 创建生产工单的正常入口
- [x] 让 dedupe 和 Firecrawl 只能使用工单绑定 URL
- [x] 空池时停止并提示运行发现 Skill
- [x] 验证并发不重复领取、技术中断可恢复

## 任务 4：核验后二次审核

- [x] 使用同一角色文件启动新的审核 subagent
- [x] 保存核验后价值报告
- [x] `write` 和 `submit` 强制检查第二次审核为 go
- [x] weak/reject lead 移入 rejected
- [x] 发布成功移入 consumed，失败保持 claimed
- [x] 验证 breakout 和 human override 不能绕过二次审核

## 任务 5：人工提升与表现反馈

- [x] 增加带原因的 `promote`
- [x] 保留原 verdict 并记录 `human-override`
- [x] 增加可选 `record-performance`
- [x] 计算每千次曝光互动
- [x] 有数据则注入后续发现审核，无数据则跳过

## 任务 6：安装与文档

- [x] 安装脚本加入新 Skill
- [x] Agent 与 Claude 市场清单加入新 Skill
- [x] README 更新为两条独立流水线
- [x] 工作流决策文档记录线索池和两次审核
- [x] 验证 `_shared/agents` 随安装复制

## 任务 7：回归与发布

- [x] 跑完整单元测试
- [x] 跑 shell 语法和 JSON 解析检查
- [x] 跑发现到发布的端到端状态测试
- [x] 确认人工审批、官方 X API、失败不自动重试规则未退化
- [x] 更新版本和 CHANGELOG
- [x] 最终核对 `tasks/plan.md` 的完成定义
