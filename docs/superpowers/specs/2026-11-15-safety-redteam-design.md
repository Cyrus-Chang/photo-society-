# 内容与模型安全层红队与语义闸门设计

## 意图

把拍社安全层从“有规则”提升为“有红队证据”：保留现有零依赖规则，增加 30 条绕过集、可热加载配置、复用已有 CLIP 文本编码器的语义相似度闸门、本地脱敏审计日志，以及输出文案的事实/联系方式联动校验。

## 目标

- 覆盖同义改写、拼音/谐音、拆字/分隔、外文、emoji、多轮诱导 30 条红队样例。
- 同一数据集分别报告纯词表与组合闸门的漏检率/通过率、分桶召回率和 20 条正常需求误杀率。
- 词表、正则、CLIP 锚点和阈值放入 JSON，带规则版本并在接口返回。
- 被拦请求写原因码、脱敏片段和时间；手机号/微信号不得以明文落盘。
- 文案的标题、简介、标签均经过联系方式过滤，实体/日期/地点/人物/器材事实必须来自输入事实。
- 20 条正常摄影需求误杀率为 0。

## 非目标与约束

- 不新增依赖，不引入涉政/涉黄词表。
- 不触碰 DiscoverPage、MarketPage、MarketPostCard、styles.css。
- CLIP 不可用时仍可运行规则闸门，并在结果中标明语义层未启用。

## 方案

采用现有 `pipeline/safety.py` 的组合闸门：输入先做 Unicode/空白/emoji/分隔归一化，再跑 JSON 规则；命中高危或注入直接 block，低危 review。规则未命中时，如果 CLIP 已加载，计算输入与高危锚点的余弦相似度：`>= block_threshold` block，`>= review_threshold` review。阈值来自配置中的校准说明和红队扫描结果，默认只让“明确接近高危语义”的文本升级，避免正常摄影需求误杀。多轮调用把最近上下文拼接后再检查，并返回首个升级轮次。

规则配置采用 `ai-classifier/config/safety.json`，启动时读取，按 mtime 自动刷新；接口统一返回 `ruleVersion`。审计使用标准库 `logging` 写 `ai-classifier/logs/safety-audit.jsonl`，片段先做手机号、微信、邮箱、URL 脱敏并限制长度。

红队数据和 20 条正常集放在 `ai-classifier/tools/safety_redteam_cases.jsonl`，评估脚本输出 JSON/CSV 汇总和漏检清单到 `.review-tmp/`。语义对比在同一脚本中通过可注入编码器或服务状态运行；无 CLIP 时明确标注 `semantic_unavailable`，不伪造分数。

## 交付验收

`tools/test_safety_mcp.py` 全绿；红队脚本输出两套漏检率及漏检清单、误杀率；FastAPI `/v1/safety/check` 和 BFF 别名返回 `ruleVersion`；审计日志不含明文手机号/微信号；文案安全测试覆盖 tags 和未知实体拒稿。
