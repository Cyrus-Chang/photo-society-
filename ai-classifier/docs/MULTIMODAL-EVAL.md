# 多模态识别回归评估

`tools/eval_multimodal.py` 是不依赖第三方库的回归脚本。它从 `labels.csv` 按题材轮流抽取 30 张图片，调用正在运行的 FastAPI 服务并输出：

- 题材门控前后的混淆表（服务同时提供 `subjectRaw` / `subjectVisible` 时分开统计）；
- `needsReview` 出现次数和每张样本的耗时；
- 首次请求、热态连续请求 4 次、并发 4 请求及并发退化比；
- 从 `src/data/mock.ts` 读取的本地人工人像样本的门控前后误报率。

## 运行

在 `ai-classifier` 目录执行：

```powershell
.\.venv\Scripts\python.exe tools\eval_multimodal.py --start-server
```

如果服务已由其他进程启动：

```powershell
.\.venv\Scripts\python.exe tools\eval_multimodal.py --url http://127.0.0.1:8100
```

结果写入仓库根目录的 `.review-tmp/multimodal-eval.json`。`--skip-perf` 可跳过性能段，`--sample-count` 可改变回归样本数。
服务不可用时脚本仍会写失败报告并返回非 0；排查时可用 `EVAL_HEALTH_TIMEOUT_SEC=2` 缩短等待时间。

如果补齐了 20 张人工确认的人像图片，可用 `--portrait-manifest path/to/portraits.txt`（每行一个路径；也支持 JSON 数组）纳入同一份前后对比报告。

## 样本边界

题材回归使用仓库已有的 672 张带 `labels.csv` 标签的图片，不把模型输出当作真值。人像误报率只使用本地文件且 `mock.ts` 明确标记 `types` 含“人像”的图片；当前仓库可发现 10 张，达不到验收要求的 20 张时，脚本会输出 `sufficientFor20=false` 和限制说明，不会用远程图片或推断标签补齐。

首请求只有在 `--start-server` 下才可视为本次进程的近似冷启动；否则它只是现有服务进程收到的首个请求。脚本不把服务未启动、模型加载失败或样本不足伪装成性能数字。
