<script setup lang="ts">
import { computed, ref, watch } from "vue"
import { RouterLink, RouterView, useRoute } from "vue-router"
import { api } from "../api"

defineProps<{ themeName: string }>()
const emit = defineEmits<{ toggleTheme: [] }>()
const route = useRoute()

const writing = computed(() => route.path.startsWith("/write/"))
const novelId = computed(() => (route.path.startsWith("/novels/") && typeof route.params.novelId === "string" ? route.params.novelId : ""))
const worldId = computed(() => (typeof route.params.worldId === "string" ? route.params.worldId : ""))
const characterId = computed(() => (typeof route.params.characterId === "string" ? route.params.characterId : ""))
const inNovel = computed(() => Boolean(novelId.value))
const inWorld = computed(() => Boolean(worldId.value))
const inCharacter = computed(() => Boolean(characterId.value))
const contextTitle = ref("")
const resourcesOpen = ref(localStorage.getItem("sf-nav-resources") !== "0")

const novelLinks = [
  { section: "overview", label: "概览" },
  { section: "world", label: "世界" },
  { section: "characters", label: "角色" },
  { section: "articles", label: "文章" },
  { section: "outline", label: "大纲" },
  { section: "foreshadows", label: "伏笔" },
]
const worldLinks = [
  ["overview", "世界概览"],
  ["setting", "基础设定"],
  ["objects", "世界观对象"],
  ["map", "地理与地图"],
  ["factions", "势力组织"],
  ["places", "地点管理"],
  ["characters", "世界角色"],
  ["timeline", "历史与时间线"],
  ["novels", "关联小说"],
] as const
const characterLinks = [
  ["overview", "角色概览"],
  ["profile", "基础档案"],
  ["periods", "角色时期"],
  ["relations", "人物关系"],
  ["worlds", "所属世界"],
  ["novels", "出场小说"],
  ["assets", "素材管理"],
  ["ai", "角色 AI"],
] as const

watch(resourcesOpen, (open) => localStorage.setItem("sf-nav-resources", open ? "1" : "0"))

watch([novelId, worldId, characterId], async () => {
  contextTitle.value = ""
  try {
    if (novelId.value) contextTitle.value = (await api.novel(novelId.value)).title
    else if (worldId.value) contextTitle.value = (await api.worldRelations(worldId.value)).name
    else if (characterId.value) {
      const rows = await api.characters()
      contextTitle.value = rows.find((row) => row.id === characterId.value)?.name || "角色"
    }
  } catch {
    contextTitle.value = ""
  }
}, { immediate: true })

function activePath(path: string) {
  return route.path === path
}
</script>

<template>
  <RouterView v-if="writing" />
  <div v-else class="shell">
    <aside class="nav">
      <div class="nav-home">
        <RouterLink class="brand" to="/">
          <strong>StoryForge</strong>
          <span :class="{ 'novel-name': inNovel && contextTitle }">{{ contextTitle || "故事工坊" }}</span>
        </RouterLink>
      </div>
      <nav v-if="inNovel" class="nav-links" aria-label="小说功能">
        <RouterLink
          v-for="item in novelLinks"
          :key="item.section"
          class="nav-link"
          :to="`/novels/${novelId}/${item.section}`"
          :class="{ active: route.params.section === item.section || (item.section === 'outline' && route.path.includes('/outline')) }"
        >{{ item.label }}</RouterLink>
      </nav>
      <nav v-else-if="inWorld" class="nav-links" aria-label="世界工作区">
        <RouterLink
          v-for="[section, label] in worldLinks"
          :key="section"
          class="nav-link"
          :to="{ path: `/worlds/${worldId}/${section}`, query: route.query }"
          :class="{ active: route.params.section === section }"
        >{{ label }}</RouterLink>
      </nav>
      <nav v-else-if="inCharacter" class="nav-links" aria-label="角色工作区">
        <RouterLink
          v-for="[section, label] in characterLinks"
          :key="section"
          class="nav-link"
          :to="{ path: `/characters/${characterId}/${section}`, query: route.query }"
          :class="{ active: route.params.section === section }"
        >{{ label }}</RouterLink>
      </nav>
      <nav v-else class="nav-links" aria-label="主要功能">
        <RouterLink class="nav-link" to="/" :class="{ active: activePath('/') }">工作台</RouterLink>
        <RouterLink class="nav-link" to="/novels" :class="{ active: activePath('/novels') }">小说项目</RouterLink>
        <button class="nav-link nav-group" type="button" @click="resourcesOpen = !resourcesOpen">
          全局资源库 {{ resourcesOpen ? "−" : "+" }}
        </button>
        <div v-show="resourcesOpen" class="nav-sub">
          <RouterLink class="nav-link" to="/worlds" :class="{ active: route.path.startsWith('/worlds') }">世界库</RouterLink>
          <RouterLink class="nav-link" to="/characters" :class="{ active: route.path === '/characters' }">角色库</RouterLink>
        </div>
      </nav>
      <div class="nav-spacer"></div>
      <RouterLink v-if="!inNovel && !inWorld && !inCharacter" class="nav-link" to="/settings" :class="{ active: activePath('/settings') }">设置</RouterLink>
      <button class="nav-theme" type="button" @click="emit('toggleTheme')">
        {{ themeName === "dark" ? "浅色" : "深色" }}
      </button>
    </aside>
    <main class="workspace">
      <RouterView />
    </main>
  </div>
</template>
