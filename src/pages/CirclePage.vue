<script setup lang="ts">
import { ArrowRight } from 'lucide-vue-next'
</script>

<template>
  <div class="circle-page">
    <p class="circle-eyebrow">圈子 · COMPANION CIRCLE</p>
    <h1>这里还没建好。</h1>
    <p class="circle-lede">
      圈子是「找拍摄搭子」的地方：同一场拍摄、同一个地点，找到愿意一起出现、互相掌机的人。
      它和首页（看作品、约拍）是两件事，所以单独一页。
    </p>

    <div class="circle-todo">
      <strong>等你拍板的三件事</strong>
      <ul>
        <li>圈子怎么分：按城市、主题，还是按拍摄题材？</li>
        <li>一条圈子帖要写哪些字段（时间 / 地点 / 人数 / 是否需要审核）？</li>
        <li>和接拍里的「搭子帖」是什么关系：合并、拆开，还是圈子只做长期组织？</li>
      </ul>
    </div>

    <div class="circle-actions">
      <router-link class="button" to="/">回到首页</router-link>
      <router-link class="button button-secondary" to="/market">先去接拍看搭子帖 <ArrowRight :size="15" /></router-link>
    </div>
  </div>
</template>

<style scoped>
.circle-page {
  max-width: 760px;
  margin: 0 auto;
  padding: clamp(56px, 9vh, 120px) clamp(20px, 5vw, 40px) 90px;
  display: grid;
  gap: 20px;
}
.circle-eyebrow {
  margin: 0;
  color: var(--coral);
  font-size: 10px;
  letter-spacing: .16em;
  text-transform: uppercase;
}
.circle-page h1 {
  margin: 0;
  font-family: var(--display);
  font-size: clamp(32px, 5vw, 54px);
  font-weight: 500;
  line-height: 1.12;
  letter-spacing: -.02em;
}
.circle-lede {
  margin: 0;
  max-width: 560px;
  color: var(--ink-600);
  font-size: 13px;
  line-height: 1.95;
}
.circle-todo {
  display: grid;
  gap: 10px;
  margin-top: 6px;
  padding: 18px 20px;
  border: 1px solid var(--paper-200);
  border-radius: 16px;
  background: var(--paper-100);
}
.circle-todo strong { font-size: 12px; letter-spacing: .04em; }
.circle-todo ul { margin: 0; padding-left: 18px; display: grid; gap: 7px; }
.circle-todo li { color: var(--ink-600); font-size: 12px; line-height: 1.8; }
.circle-actions { display: flex; flex-wrap: wrap; gap: 12px; margin-top: 8px; }
</style>
