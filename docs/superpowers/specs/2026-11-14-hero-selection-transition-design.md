# Hero Selection Transition Design

**Date:** 2026-11-14

## Intent

点击照片时，当前照片平滑放大并向左移动，详情面板从右侧进入；关闭或返回首页时只清除选中状态，背景图不重新挂载、不复制、不缩放、不改变裁切。

## Goals

- 让选中图片的运动路径明确：向左、放大、一次完成。
- 让详情面板固定从右侧进入，不落到页面底部。
- 保留一张原始 `hero-stars.webp` `<img>`，点击前后规格完全一致。
- 复用现有作品数据和 `localWorkUrl()`，避免标题与图片错配。

## Non-goals

- 不改首页文案、导航、粒子、流星、后续区块或上传流程。
- 不复制背景图做交叉淡入，也不新增背景层。

## Constraints

- 背景：`src/assets/hero-stars.webp`，`object-fit: cover`，`object-position: center 48%`，`width: 100%`，`height: 100%`。
- 选中状态只改变照片卡、详情层和标题模块的可见性。
- 作者没有填写的介绍保持为空。
- 作品图片地址必须从 `works` + `localWorkUrl()` 得到。
