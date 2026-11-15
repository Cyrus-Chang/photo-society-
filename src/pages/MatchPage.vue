<script setup lang="ts">
import { ArrowLeft } from 'lucide-vue-next'
import AgentMatch from '../components/AgentMatch.vue'
</script>

<template>
  <div class="match-page">
    <header class="match-head">
      <RouterLink class="match-back" to="/discover"><ArrowLeft :size="15" />回到约拍</RouterLink>
      <span class="match-eyebrow">AI MATCH / 2026</span>
      <h1>一句话，<em>说完你要的现场。</em></h1>
      <p>模型会先把你的需求拆成槽位，再去作品库里做向量检索、核对城市与档期，最后给出候选摄影师和推荐理由。每一步工具调用都可以展开核对——不做黑箱。</p>
    </header>

    <AgentMatch />
  </div>
</template>
