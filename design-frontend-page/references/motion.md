# Motion discipline

动效必须服务于页面任务。数字是基准，不是为了堆动画：如果现有产品已经有时长或缓动，先复用它。

## 基准

| 场景 | 时长 | 建议缓动 |
|---|---:|---|
| hover / focus 反馈 | 120–180ms | ease-out |
| 卡片进入 | 220–320ms | cubic-bezier(.22, 1, .36, 1) |
| 面板展开 | 280–400ms | ease-in-out |
| 开场 signature | 400ms 以内，确需叙事时再延长 | 与内容节奏一致 |

一页保持 1 个 signature effect 和 2–4 个 support。不要让多个循环动画同时争夺首屏注意力。

## reduced-motion

```css
@media (prefers-reduced-motion: reduce) {
  *, *::before, *::after {
    animation-duration: 1ms !important;
    animation-iteration-count: 1 !important;
    scroll-behavior: auto !important;
    transition-duration: 1ms !important;
  }
}
```

## 截图闭环

1. 截图首屏、关键交互和移动端。
2. 只记录会改变判断的问题：层级、节奏、遮挡、溢出、可读性、动效抢焦点。
3. 修复后在同一尺寸重截；如果没有第二轮截图，交付中明确写未复核。
