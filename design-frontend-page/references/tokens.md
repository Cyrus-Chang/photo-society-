# Token extraction and implementation

从 awesome-design-md 只抽结构，不复制配色和文案。先读一份深色产品画布和一份图片网格型消费品牌，归纳层级，再映射到现有项目变量。

## 最小 token 集

每页至少明确这些 token；已有变量优先复用：

```css
:root {
  --color-bg: var(--existing-bg);
  --color-surface: var(--existing-surface);
  --color-ink: var(--existing-ink);
  --color-muted: var(--existing-muted);
  --size-xs: 12px;
  --size-sm: 14px;
  --size-md: 16px;
  --size-lg: 24px;
  --size-xl: 40px;
  --space-1: 4px;
  --space-2: 8px;
  --space-3: 16px;
  --space-4: 24px;
  --radius: 12px;
  --shadow: var(--existing-shadow);
}
```

上面只是结构示例。把项目已有值填入，不要因为示例而新增裸色或重复变量。用户明确给出的品牌变量（例如 `--coral:#e98b6b`）可以保留。

## 记录方式

为每个 token 写用途、来源和替换范围：

```text
token：--space-3
用途：卡片内主要分组间距
来源：现有页面 / design-md 结构参照
验证：375 与 1440 下无拥挤、无溢出
```

字号至少覆盖正文、辅助、标签、标题和展示级；色阶至少覆盖背景、表面、正文、弱文本、边界和状态；间距至少覆盖 4 级。组件状态必须沿用同一层级关系。
