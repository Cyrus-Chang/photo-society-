---
name: design-frontend-page
description: Use when designing, implementing, or reviewing a frontend page where visual direction, tokens, motion, native effects, and screenshot-based QA must be decided as one workflow. Works with Vue, React, or plain HTML and preserves existing project constraints.
---

# Design Frontend Page

把设计情报、token、布局、原生视觉效果、动效和验收串成一条流水线。这个 skill 适合新页面、重要页面改版和需要目视验收的组件；小型 bug 修复、纯后端任务和不涉及视觉决策的文案改动不使用它。

## 不可变的工作原则

- 先读现状再设计：复用项目已有 CSS 变量、字号阶梯、间距和组件状态，不另起一套 token。
- 设计情报是候选和验收依据，不是模板库；不照抄品牌配色、文案或页面结构。
- 项目禁止新增依赖时，threeui 只提供效果词汇，必须用现有能力和原生 CSS/canvas 复刻。
- 一页只选 1 个 signature effect，另配 2–4 个 support；效果不能抢主任务。
- 不编造数字、评分、评价或来源。接口降级时，界面要标明真实数据来源和统计口径。
- 没有截图就不能宣布目视验收完成；只能写“未做目视确认”。

## 七步流程

1. **读现状**：读入口页面、相邻组件、现有样式、数据/API、响应式断点和约束。记录哪些变量、组件和动效必须复用。
2. **写 brief 卡**：写清产品类型、目标用户、页面要解决的一件事、首屏主任务、内容密度、已知禁区和验收断点。
3. **检索情报**：按产品类型用 UI UX Pro Max 取主风格、1–2 个辅助风格、色板、字体配对、UX 规则和 `vue.csv` 栈规范。把结果写进 brief，不直接生成代码。
4. **定 token**：只读 awesome-design-md 中一份深色产品画布和一份图片网格型消费品牌，抽取分层色阶、字号阶梯、间距节奏、圆角、阴影和状态结构；不要复制它们的颜色或文案。参考 [tokens.md](references/tokens.md)。
5. **排布局**：先决定图片优先还是信息优先，再安排首屏和分屏节奏。先完成可用的 loading、empty、error、focus 和窄屏结构。
6. **做效果与动效**：从 [effects.md](references/effects.md) 选一个 signature，用原生 CSS/canvas 实现；按 [motion.md](references/motion.md) 配时长、缓动、进入、悬停和 `prefers-reduced-motion`。
7. **验收闭环**：按 [acceptance.md](references/acceptance.md) 在 375/390/768/1440 检查，截图并记录问题，修复后再次截图；把 UI UX Pro Max 规则和 `vue.csv` 规范逐项勾选。

## 五个来源如何分工

- UI UX Pro Max：情报检索层，负责选型和 UX/栈审查项。
- awesome-design-md：token 精度参照，只借结构和状态分层。
- threeui：效果词典，只借颗粒、半调、点阵、金属高光、流动场等手法。
- motionsites：动效纪律和截图打分修复闭环。
- MeiGen：氛围图、空态图提示词；使用五段式主体/场景/光线/质感/构图，声明尺寸、参考图角色和禁区，不承担主视觉信息架构。

## 按需读取的参考文件

- 需要把检索结果变成清单时读 [ux-rules.md](references/ux-rules.md)。
- 需要命名和落地 token 时读 [tokens.md](references/tokens.md)。
- 需要原生复刻视觉手法时读 [effects.md](references/effects.md)。
- 需要设计进入、悬停和 reduced-motion 时读 [motion.md](references/motion.md)。
- 需要截图、评分和交付证据时读 [acceptance.md](references/acceptance.md)。

## 交付格式

交付时说明：brief 决策、复用的现有 token、signature/support 效果、改动文件与行为、截图和命令证据、未完成的目视验证、剩余冲突。不要用“看起来完成了”替代证据。
