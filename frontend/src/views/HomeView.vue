<script setup lang="ts">
import { computed, onMounted, ref } from "vue"
import { useRouter } from "vue-router"
import { api } from "../api"
import type { Foreshadow, Novel, PendingSuggestion, World } from "../types"

const router = useRouter()
const novels = ref<Novel[]>([])
const worlds = ref<World[]>([])
const inbox = ref<Foreshadow[]>([])
const pending = ref<PendingSuggestion[]>([])

const totalWords = computed(() => novels.value.reduce((sum, novel) => sum + novel.word_count, 0))
const totalChapters = computed(() => novels.value.reduce((sum, novel) => sum + novel.chapter_count, 0))

onMounted(async () => {
  ;[novels.value, worlds.value, inbox.value, pending.value] = await Promise.all([
    api.novels(),
    api.worlds(),
    api.foreshadowInbox(),
    api.pendingSuggestions(),
  ])
})

function openNovel(id: string) {
  void router.push(`/novels/${id}/overview`)
}
function openWorld(id: string) {
  void router.push(`/worlds/${id}/overview`)
}
</script>

<template>
  <main class="page">
    <header class="workspace-head">
      <div>
        <h1>工作台</h1>
        <p class="muted">最近在写的内容和当前进度。</p>
      </div>
    </header>
    <section class="stats">
      <article class="card stat"><strong>{{ novels.length }}</strong><span>小说</span></article>
      <article class="card stat"><strong>{{ totalChapters }}</strong><span>章节</span></article>
      <article class="card stat"><strong>{{ totalWords }}</strong><span>字</span></article>
      <article class="card stat"><strong>{{ worlds.length }}</strong><span>世界</span></article>
    </section>
    <section class="split">
      <div>
        <div class="section-title"><strong>最近编辑</strong></div>
        <button v-for="novel in novels.slice(0, 6)" :key="novel.id" class="card row-card linkish" type="button" @click="openNovel(novel.id)">
          <div>
            <strong>{{ novel.title }}</strong>
            <div class="meta"><span>{{ novel.word_count }} 字</span><span>{{ novel.chapter_count }} 章</span></div>
          </div>
        </button>
        <p v-if="novels.length === 0" class="empty">还没有小说。可以到小说项目里创建。</p>
      </div>
      <div>
        <div class="section-title"><strong>最近使用的世界</strong></div>
        <button v-for="world in worlds.slice(0, 6)" :key="world.id" class="card row-card linkish" type="button" @click="openWorld(world.id)">
          <strong>{{ world.name }}</strong>
          <span class="muted">{{ world.novel_count }} 本小说</span>
        </button>
        <div v-if="inbox.length" class="panel inbox">
          <strong>待回收伏笔</strong>
          <button v-for="item in inbox" :key="item.id" class="text-button" type="button" @click="router.push(`/novels/${item.novel_id}/foreshadows`)">
            {{ item.novel_title }} · {{ item.name }}
          </button>
        </div>
        <div v-if="pending.length" class="panel inbox">
          <strong>待确认建议</strong>
          <button v-for="item in pending" :key="item.id" class="text-button" type="button" @click="router.push(`/write/${item.novel_id}/${item.chapter_id}`)">
            {{ item.novel_title }} · {{ item.chapter_title }}
          </button>
        </div>
      </div>
    </section>
  </main>
</template>
