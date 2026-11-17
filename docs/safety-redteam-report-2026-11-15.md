# 拍社安全层红队报告（2026-11-15）

## 数据与方法

红队集位于 `ai-classifier/tools/safety_redteam_cases.jsonl`，共 30 条：同义改写、私单绕过、拼音/谐音、拆字/分隔、外文、emoji、多轮诱导各 5 条。正常集位于 `ai-classifier/tools/safety_benign_cases.jsonl`，共 20 条。多轮样例按 turn 累积检查，并记录首次升级轮次。

评估脚本：

```powershell
cd E:\通用型摄影师接单平台\ai-classifier
.\.venv\Scripts\python.exe tools\run_safety_redteam.py
```

结果文件写入 `.review-tmp/redteam_summary.json`、`.review-tmp/redteam_results.csv` 和 `.review-tmp/redteam_misses.json`。

## 结果

| 方案 | 红队漏检率 | 红队通过率 | 正常集误杀率 |
|---|---:|---:|---:|
| 规则（归一化 + 词表/正则） | 83.33%（25/30） | 83.33% | 0%（0/20） |
| 规则 + CLIP 语义闸门 | 76.67%（23/30） | 76.67% | 0%（0/20） |

组合闸门最终动作是 block 5、review 2、pass 23。CLIP 使用现有 `openai/clip-vit-base-patch32` 文本编码器，配置文件为 `ai-classifier/config/safety.json`。20 条正常输入的最高余弦相似度为 `0.989475`，因此采用 `review=0.990`、`block=0.992`；阈值来源和版本号随接口返回。阈值选择优先满足正常集误杀率为 0，再取红队中可区分的起始值。

## 当前仍能绕过的样例

组合闸门的漏检清单为：

`R03 R04 R06 R07 R08 R09 R10 R11 R13 R15 R17 R18 R20 R21 R22 R23 R24 R25 R26 R27 R28 R29 R30`

它们主要是：私单绕过的间接说法、带空格的拼音、英文描述、拆分后的联系方式，以及多轮中没有出现现有高危短语的诱导。英文 CLIP 与中文高危锚点的跨语言对齐很弱；中文句子之间的相似度又偏高，继续降低阈值会把正常需求误杀，所以本轮没有把阈值调到能覆盖这些样例。它们已保留在漏检 JSON 中，作为下一轮规则/锚点扩充数据，不应宣称语义层可以替代模型或人工复核。

## 已落地的审计与输出联动

- `pipeline/safety.py` 热加载 JSON 规则，返回 `ruleVersion`、`reasonCodes`、语义分数和 `escalatedTurn`。
- 被 block/review 的请求写入 `ai-classifier/logs/safety-audit.jsonl`；片段先脱敏手机号、微信号、邮箱、外链，再限制长度。`GET /v1/safety/audit` 和 `/api/v1/ai/safety/audit` 可查询最近记录。
- `pipeline/agent.py` 在检索和 LLM 前传入同一个 CLIP 状态；CLIP 不可用时降级为规则，不伪造相似度。
- `pipeline/copywriter.py` 的标题、简介、标签都经过联系方式过滤；已有日期、地点、人物、器材事实校验继续拒绝模型编造实体。

## 验收命令

```powershell
.\.venv\Scripts\python.exe tools\test_safety_core.py
.\.venv\Scripts\python.exe tools\test_safety_audit.py
.\.venv\Scripts\python.exe tools\test_copywriter.py
.\.venv\Scripts\python.exe tools\run_safety_redteam.py
.\.venv\Scripts\python.exe tools\test_safety_mcp.py
```

其中 MCP 脚本的安全 5/5 用例保持全绿；需要已启动 8100 服务的 MCP 转发部分会按环境报告服务可用性。
