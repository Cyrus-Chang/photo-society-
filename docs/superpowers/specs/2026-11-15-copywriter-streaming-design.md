# 作品文案生成闭环设计

## 意图

把上传弹窗中的作品文案从“代码就绪”提升到可现场演示：真实 OpenAI 兼容调用可观测，模型输出有结构校验和事实拒稿，失败时明确降级，前端能逐字显示流式简介。

## 目标

- 同步和 SSE 接口共用同一套 prompt、重试、schema 校验、事实校验和 rule 降级。
- 记录 prompt 版本、model、耗时、token 用量、尝试次数和错误码，并提供进程内 P50/P95。
- 对日期、地名、人名、器材做输入事实白名单校验；未知事实拒稿并重试，仍失败则降级。
- 无 key 时只返回 `mode=rule`，不声称真实 LLM 已联调。

## 非目标与约束

- 不新增依赖，HTTP 继续使用标准库 `urllib`。
- 不改 DiscoverPage、MarketPage、MarketPostCard；前端只改上传弹窗链路和 `ai-copy-panel` 末尾样式。
- 不把 rule 结果伪装成模型结果；prompt 保留不编造时间、地点、人物身份/关系、拍摄经过三条红线。

## 方案

采用 FastAPI `StreamingResponse` 暴露 `/v1/copywrite/stream`，BFF 同步映射到 `/api/v1/ai/copywrite/stream`。上游以 OpenAI 兼容 SSE 传输 JSON 增量，后端仅提取已完成的 `intro` 字符给浏览器；完整 JSON 在服务端校验后通过 `result` 事件发送。同步 `/v1/copywrite` 复用相同生成器的非流式路径。

独立的 `pipeline/prompts.py` 持有 `COPYWRITER_PROMPT_VERSION` 和 system prompt。`pipeline/copywriter.py` 负责 schema、事实校验、重试、日志、指标和降级；`tools/test_copywriter.py` 负责无 key 冒烟、20 条对抗样例和指标输出。

## 接口事件

- `meta`: `mode`、`model`、`promptVersion`
- `delta`: `{field: "intro", text: "..."}`
- `reset`: 重试前清空上一次半截输出
- `result`: 完整 `CopyResult`
- `done`: 成功模式和耗时
