# Native effect dictionary

threeui 只提供手法名称和观察角度。项目禁止新增依赖时，不安装 `threeui` 或其他渲染包；优先用 CSS pseudo-element、`background-image`、`filter`、SVG 或现有 canvas。

## 手法 → 原生实现

| 手法 | 原生实现 | 使用边界 |
|---|---|---|
| 颗粒 | `::before` + repeating-radial-gradient + 低 opacity | 只做背景层，不能盖住正文 |
| 半调网点 | radial-gradient 多层叠加，控制 background-size | 用于图片区或 hover，避免全屏噪声 |
| 点阵 | repeating-linear/radial-gradient | 用于分隔、状态或局部装饰 |
| 金属高光 | 线性渐变 + mask/clip-path + hover 位移 | 只给一个关键控件或标题 |
| 流动场 | 原生 canvas，按帧更新少量粒子 | 需要明确停止条件和 reduced-motion 降级 |

## 选择规则

1. 先写 signature 的目的：引导注意、表达材质或反馈状态。
2. 只选一个 signature；其余效果只能辅助层级、进入或悬停。
3. 给效果设预算：覆盖面积、帧率、移动端策略和关闭条件。
4. `prefers-reduced-motion` 下关闭位移、粒子和循环动画，保留静态纹理或淡入。
