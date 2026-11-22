<script setup lang="ts">
import { NButton, NForm, NFormItem, NInput, NModal, NSelect, useDialog, useMessage } from "naive-ui"
import { computed, reactive, ref, watch } from "vue"
import { useRoute, useRouter } from "vue-router"
import { api } from "../api"
import CoverField from "../components/CoverField.vue"
import { characterCovers, coverSrc, worldCovers } from "../covers"
import type { ChapterBrief, Character, Foreshadow, NovelDetail, OutlineDraftNode, OutlineNode, World } from "../types"

const route = useRoute()
const router = useRouter()
const message = useMessage()
const dialog = useDialog()
const novel = ref<NovelDetail | null>(null)
const worlds = ref<World[]>([])
const allCharacters = ref<Character[]>([])
const linkedCharacterIds = ref<string[]>([])
const nodes = ref<OutlineNode[]>([])
const foreshadows = ref<Foreshadow[]>([])
const worldIds = ref<string[]>([])
const menuKey = ref("")
const addWorldOpen = ref(false)
const addCharacterOpen = ref(false)
const worldCreateOpen = ref(false)
const characterCreateOpen = ref(false)
const foreshadowOpen = ref(false)
const foreshadowMore = ref(false)
const collapsed = ref(new Set<string>())
const ignoreDrag = ref(false)
const worldForm = reactive({ name: "", summary: "", cover_url: worldCovers[0].url })
const characterForm = reactive({ name: "", summary: "", cover_url: characterCovers[0].url })
const outlineReport = ref("")
const draft = ref<OutlineDraftNode[] | null>(null)
const draftProvider = ref("")
const instruction = ref("")
const filterStatus = ref<string | null>(null)
const filterImportance = ref<string | null>(null)
const foreshadowForm = reactive({
  id: "",
  name: "",
  content: "",
  kind: "",
  importance: "medium",
  status: "planned",
  outline_node_id: null as string | null,
  plant_chapter_id: null as string | null,
  expected_chapter_id: null as string | null,
  actual_chapter_id: null as string | null,
  source_quote: "",
  source_start: null as number | null,
  source_end: null as number | null,
  notes: "",
  character_ids: [] as string[],
})
const foreshadowReview = ref<{ foreshadow_id: string; name: string; reason: string; proposed_status: string | null }[]>([])
const foreshadowReviewReport = ref("")
const foreshadowDraft = ref<Partial<Foreshadow> | null>(null)
const draggingId = ref("")
const foreshadowHint = ref("")

const novelId = computed(() => String(route.params.novelId))
const section = computed(() => String(route.params.section || "articles"))
const chapterOptions = computed(() => (novel.value?.chapters ?? []).map((chapter) => ({ label: chapter.title, value: chapter.id })))
const nodeOptions = computed(() => nodes.value.map((node) => ({ label: node.title, value: node.id })))
const linkedCharacterOptions = computed(() => (novel.value?.characters ?? []).map((row) => ({ label: row.name, value: row.id })))
const linkedWorldCards = computed(() => (novel.value?.worlds ?? []).flatMap((row) => {
  const world = worlds.value.find((item) => item.id === row.id)
  return world ? [world] : []
}))
const linkedCharacterCards = computed(() => (novel.value?.characters ?? []).flatMap((row) => {
  const character = allCharacters.value.find((item) => item.id === row.id)
  return character ? [character] : []
}))
const availableWorldOptions = computed(() => worlds.value.filter((row) => !worldIds.value.includes(row.id)).map((row) => ({ label: row.name, value: row.id })))
const availableCharacterOptions = computed(() => allCharacters.value.filter((row) => !linkedCharacterIds.value.includes(row.id)).map((row) => ({ label: row.name, value: row.id })))
const orderedNodes = computed(() => {
  const result: OutlineNode[] = []
  const walk = (parentId: string | null) => {
    for (const node of childrenOf(parentId)) {
      result.push(node)
      walk(node.id)
    }
  }
  walk(null)
  return result
})
const visibleNodes = computed(() => orderedNodes.value.filter((node) => {
  let cursor = node.parent_id
  const seen = new Set<string>()
  while (cursor && !seen.has(cursor)) {
    if (collapsed.value.has(cursor)) return false
    seen.add(cursor)
    cursor = nodes.value.find((item) => item.id === cursor)?.parent_id ?? null
  }
  return true
}))

const outlineStatus = [
  { label: "未开始", value: "pending" },
  { label: "进行中", value: "active" },
  { label: "已完成", value: "done" },
]
const foreshadowStatus = [
  { label: "待埋设", value: "planned" },
  { label: "已埋设", value: "planted" },
  { label: "待回收", value: "pending_payoff" },
  { label: "已回收", value: "paid" },
  { label: "已废弃", value: "discarded" },
]
const importanceOptions = [
  { label: "低", value: "low" },
  { label: "中", value: "medium" },
  { label: "高", value: "high" },
]

function sectionTitle(name: string) {
  return { overview: "概览", world: "世界", characters: "角色", articles: "文章", outline: "大纲", foreshadows: "伏笔" }[name] ?? "小说"
}

function resourcePath(kind: "worlds" | "characters", id: string) {
  return { path: `/${kind}/${id}/overview`, query: { from: `/novels/${novelId.value}/${section.value}` } }
}

function labelOf(options: { label: string; value: string }[], value: string) {
  return options.find((item) => item.value === value)?.label ?? value
}

function childrenOf(parentId: string | null) {
  return nodes.value
    .filter((node) => node.parent_id === parentId)
    .sort((a, b) => a.position - b.position)
}

function hasChildren(id: string) {
  return nodes.value.some((node) => node.parent_id === id)
}

function toggleFold(id: string) {
  const next = new Set(collapsed.value)
  if (next.has(id)) next.delete(id)
  else next.add(id)
  collapsed.value = next
}

function depth(node: OutlineNode) {
  let level = 0
  let cursor = node.parent_id
  const seen = new Set<string>()
  while (cursor && !seen.has(cursor)) {
    seen.add(cursor)
    level += 1
    cursor = nodes.value.find((item) => item.id === cursor)?.parent_id ?? null
  }
  return level
}

async function load() {
  const detail = await api.novel(novelId.value)
  novel.value = detail
  worldIds.value = detail.worlds.map((row) => row.id)
  linkedCharacterIds.value = detail.characters.map((row) => row.id)
  menuKey.value = ""
  if (section.value === "overview" || section.value === "world") worlds.value = await api.worlds()
  if (section.value === "characters" || section.value === "outline" || section.value === "foreshadows") {
    allCharacters.value = await api.characters()
  }
  if (section.value === "outline" || section.value === "foreshadows") nodes.value = await api.outline(novelId.value)
  if (section.value === "foreshadows") await loadForeshadows()
}

async function loadForeshadows() {
  const query = new URLSearchParams()
  if (filterStatus.value) query.set("status", filterStatus.value)
  if (filterImportance.value) query.set("importance", filterImportance.value)
  const suffix = query.toString() ? `?${query}` : ""
  foreshadows.value = await api.foreshadows(novelId.value, suffix)
}

async function saveWorldLink(removed = false) {
  if (!novel.value) return
  await api.updateNovel(novel.value.id, { world_ids: worldIds.value })
  message.success(removed ? "已解除关联，世界还在" : "已关联到这本小说")
  await load()
}

async function saveCharacterLinks(removed = false) {
  if (!novel.value) return
  await api.updateNovel(novel.value.id, { character_ids: linkedCharacterIds.value })
  message.success(removed ? "已解除关联，角色还在" : "已关联到这本小说")
  await load()
}

function openCreateWorld() {
  Object.assign(worldForm, { name: "", summary: "", cover_url: worldCovers[0].url })
  worldCreateOpen.value = true
}

function openCreateCharacter() {
  Object.assign(characterForm, { name: "", summary: "", cover_url: characterCovers[0].url })
  characterCreateOpen.value = true
}

async function saveCreateWorld() {
  if (!worldForm.name.trim()) {
    message.warning("请填写世界名称")
    return
  }
  const world = await api.createWorld({ name: worldForm.name.trim(), summary: worldForm.summary, cover_url: worldForm.cover_url })
  worldIds.value = [...worldIds.value, world.id]
  worldCreateOpen.value = false
  await saveWorldLink()
}

async function saveCreateCharacter() {
  if (!characterForm.name.trim()) {
    message.warning("请填写角色姓名")
    return
  }
  const created = await api.createCharacter({ name: characterForm.name.trim(), summary: characterForm.summary, cover_url: characterForm.cover_url })
  linkedCharacterIds.value = [...linkedCharacterIds.value, created.id]
  characterCreateOpen.value = false
  await saveCharacterLinks()
}

async function pickWorld(id: string | null) {
  if (!id || worldIds.value.includes(id)) return
  worldIds.value = [...worldIds.value, id]
  addWorldOpen.value = false
  await saveWorldLink()
}

async function pickCharacter(id: string | null) {
  if (!id || linkedCharacterIds.value.includes(id)) return
  linkedCharacterIds.value = [...linkedCharacterIds.value, id]
  addCharacterOpen.value = false
  await saveCharacterLinks()
}

async function addChapter() {
  if (!novel.value) return
  await api.createChapter(novel.value.id, `第${novel.value.chapters.length + 1}章`)
  await load()
}

function removeChapter(chapter: ChapterBrief) {
  dialog.warning({
    title: "删除章节",
    content: `删除「${chapter.title}」。至少会保留一个章节。`,
    positiveText: "删除",
    negativeText: "取消",
    onPositiveClick: async () => {
      try {
        await api.deleteChapter(chapter.id)
        await load()
      } catch (error) {
        message.error(error instanceof Error ? error.message : "删除失败")
      }
    },
  })
}

async function addNode(parentId: string | null) {
  menuKey.value = ""
  const created = await api.createOutline(novelId.value, { title: "新节点", content: "", parent_id: parentId, status: "pending" })
  await router.push(`/novels/${novelId.value}/outline/${created.id}`)
}

function openNode(node: OutlineNode) {
  if (ignoreDrag.value) return
  void router.push(`/novels/${novelId.value}/outline/${node.id}`)
}

async function moveNode(node: OutlineNode, direction: "up" | "down") {
  await api.moveOutline(node.id, direction)
  nodes.value = await api.outline(novelId.value)
}

function removeNode(node: OutlineNode) {
  dialog.warning({
    title: "删除大纲节点",
    content: `删除「${node.title}」会同时删除它下面的子节点。`,
    positiveText: "删除",
    negativeText: "取消",
    onPositiveClick: async () => {
      await api.deleteOutline(node.id)
      nodes.value = await api.outline(novelId.value)
    },
  })
}

async function toChapter(node: OutlineNode) {
  if (node.chapter_id) {
    await router.push(`/write/${novelId.value}/${node.chapter_id}`)
    return
  }
  const result = await api.outlineToChapter(node.id)
  message.success("已生成章节")
  await router.push(`/write/${novelId.value}/${result.chapter_id}`)
}

function onDragStart(id: string) {
  draggingId.value = id
  ignoreDrag.value = false
}

function onDragEnd() {
  ignoreDrag.value = true
  window.setTimeout(() => {
    ignoreDrag.value = false
  }, 200)
}

async function onDrop(target: OutlineNode) {
  const source = nodes.value.find((node) => node.id === draggingId.value)
  draggingId.value = ""
  if (!source || source.id === target.id) return
  if (source.parent_id !== target.parent_id) {
    const next = nodes.value.map((node) => ({
      id: node.id,
      parent_id: node.id === source.id ? target.id : node.parent_id,
      position: node.position,
    }))
    await api.reorderOutline(novelId.value, next)
    nodes.value = await api.outline(novelId.value)
    return
  }
  const siblings = childrenOf(source.parent_id)
  const from = siblings.findIndex((node) => node.id === source.id)
  const to = siblings.findIndex((node) => node.id === target.id)
  if (from < 0 || to < 0) return
  siblings.splice(to, 0, siblings.splice(from, 1)[0])
  const positions = new Map(siblings.map((node, index) => [node.id, index + 1]))
  await api.reorderOutline(
    novelId.value,
    nodes.value.map((node) => ({ id: node.id, parent_id: node.parent_id, position: positions.get(node.id) ?? node.position })),
  )
  nodes.value = await api.outline(novelId.value)
}

async function askOutline() {
  const result = await api.draftOutline(novelId.value, instruction.value)
  draft.value = result.nodes
  draftProvider.value = result.provider
}

async function confirmDraft(items: OutlineDraftNode[], parentId: string | null) {
  for (const item of items) {
    const created = await api.createOutline(novelId.value, {
      title: item.title,
      content: item.content,
      parent_id: parentId,
      status: "pending",
    })
    if (item.children?.length) await confirmDraft(item.children, created.id)
  }
}

function expandNode(node: OutlineNode) {
  menuKey.value = ""
  void router.push({ path: `/novels/${novelId.value}/outline/${node.id}`, query: { expand: "1" } })
}

async function checkOutline() {
  const result = await api.checkOutline(novelId.value)
  outlineReport.value = result.report
}

async function acceptDraft() {
  if (!draft.value) return
  await confirmDraft(draft.value, null)
  draft.value = null
  nodes.value = await api.outline(novelId.value)
  message.success("大纲建议已写入")
}

function resetForeshadow() {
  Object.assign(foreshadowForm, {
    id: "",
    name: "",
    content: "",
    kind: "",
    importance: "medium",
    status: "planned",
    outline_node_id: null,
    plant_chapter_id: null,
    expected_chapter_id: null,
    actual_chapter_id: null,
    source_quote: "",
    source_start: null,
    source_end: null,
    notes: "",
    character_ids: [],
  })
  foreshadowMore.value = false
}

function blankForeshadow() {
  resetForeshadow()
  foreshadowOpen.value = true
}

function editForeshadow(row: Foreshadow) {
  Object.assign(foreshadowForm, row)
  foreshadowMore.value = false
  foreshadowOpen.value = true
}

async function saveForeshadow() {
  if (!foreshadowForm.name.trim()) {
    message.warning("请填写伏笔名称")
    return
  }
  const body = { ...foreshadowForm }
  if (foreshadowForm.id) await api.updateForeshadow(foreshadowForm.id, body)
  else await api.createForeshadow(novelId.value, body)
  foreshadowOpen.value = false
  resetForeshadow()
  await loadForeshadows()
}

function removeForeshadow(row: Foreshadow) {
  dialog.warning({
    title: "删除伏笔",
    content: `删除「${row.name}」。`,
    positiveText: "删除",
    negativeText: "取消",
    onPositiveClick: async () => {
      await api.deleteForeshadow(row.id)
      await loadForeshadows()
    },
  })
}

async function askForeshadow() {
  const result = await api.draftForeshadow(novelId.value, foreshadowHint.value)
  foreshadowDraft.value = result.suggestion
}

async function reviewForeshadows(kind: "forgotten" | "payoff" | "conflict") {
  const result = await api.reviewForeshadows(novelId.value, kind)
  foreshadowReview.value = result.findings
  foreshadowReviewReport.value = result.report
}

async function acceptReview() {
  for (const item of foreshadowReview.value) {
    if (item.proposed_status) await api.updateForeshadow(item.foreshadow_id, { status: item.proposed_status })
  }
  foreshadowReview.value = []
  foreshadowReviewReport.value = ""
  await loadForeshadows()
  message.success("已确认。只有带状态建议的条目被更新。")
}

function acceptForeshadowDraft() {
  if (!foreshadowDraft.value) return
  resetForeshadow()
  Object.assign(foreshadowForm, foreshadowDraft.value)
  foreshadowDraft.value = null
  foreshadowOpen.value = true
  message.info("建议已放进表单，保存后才会写入")
}

function jumpForeshadow(row: { plant_chapter_id: string | null; source_start: number | null; source_end: number | null }) {
  if (!row.plant_chapter_id) return
  const query: Record<string, string> = {}
  if (row.source_start != null && row.source_end != null) {
    query.from = String(row.source_start)
    query.to = String(row.source_end)
  }
  void router.push({ path: `/write/${novelId.value}/${row.plant_chapter_id}`, query })
}

async function unlinkWorld(id: string) {
  menuKey.value = ""
  worldIds.value = worldIds.value.filter((item) => item !== id)
  await saveWorldLink(true)
}

async function unlinkCharacter(id: string) {
  menuKey.value = ""
  linkedCharacterIds.value = linkedCharacterIds.value.filter((item) => item !== id)
  await saveCharacterLinks(true)
}

watch(() => [novelId.value, section.value, filterStatus.value, filterImportance.value], () => {
  void load().catch((error: unknown) => {
    message.error(error instanceof Error ? error.message : "加载失败")
    void router.push("/")
  })
}, { immediate: true })
</script>

<template>
  <main class="page" v-if="novel" @click="menuKey = ''">
    <header class="workspace-head pin-head">
      <h1>{{ sectionTitle(section) }}</h1>
      <div v-if="section === 'world'" class="actions">
        <NButton size="small" @click="openCreateWorld">创建并关联</NButton>
        <NButton size="small" @click.stop="addWorldOpen = !addWorldOpen">添加关联</NButton>
        <NSelect v-if="addWorldOpen" :value="null" :options="availableWorldOptions" placeholder="选择已有世界" style="width: 220px" @update:value="pickWorld" />
      </div>
      <div v-else-if="section === 'characters'" class="actions">
        <NButton size="small" @click="openCreateCharacter">创建并关联</NButton>
        <NButton size="small" @click.stop="addCharacterOpen = !addCharacterOpen">添加关联</NButton>
        <NSelect v-if="addCharacterOpen" :value="null" :options="availableCharacterOptions" placeholder="选择已有角色" style="width: 220px" @update:value="pickCharacter" />
      </div>
      <div v-else-if="section === 'articles'" class="actions">
        <NButton size="small" @click="addChapter">新增章节</NButton>
      </div>
      <div v-else-if="section === 'outline'" class="actions">
        <NButton size="small" @click="addNode(null)">添加节点</NButton>
      </div>
      <div v-else-if="section === 'foreshadows'" class="actions">
        <NSelect v-model:value="filterStatus" clearable :options="foreshadowStatus" placeholder="状态" style="width: 140px" />
        <NSelect v-model:value="filterImportance" clearable :options="importanceOptions" placeholder="重要程度" style="width: 140px" />
        <NButton size="small" @click="blankForeshadow">新建</NButton>
      </div>
    </header>

    <section v-if="section === 'overview'">
      <div class="overview-top">
        <img class="book-cover" :src="coverSrc(novel.cover_url)" alt="" />
        <div>
          <p class="overview-summary">{{ novel.summary || "还没有简介" }}</p>
          <div class="overview-stats">
            <article class="stat"><strong>{{ novel.chapter_count }}</strong><span>章节</span></article>
            <article class="stat"><strong>{{ novel.word_count }}</strong><span>字</span></article>
            <article class="stat"><strong>{{ novel.worlds.length }}</strong><span>关联世界</span></article>
            <article class="stat"><strong>{{ novel.characters.length }}</strong><span>关联角色</span></article>
          </div>
        </div>
      </div>
      <div v-if="linkedWorldCards.length" class="book-shelf">
        <article v-for="world in linkedWorldCards" :key="world.id" class="resource-card" @click="router.push(resourcePath('worlds', world.id))">
          <img class="book-cover" :src="coverSrc(world.cover_url, 'world')" alt="" />
          <div class="book-copy">
            <h2>{{ world.name }}</h2>
            <p class="summary">{{ world.summary || "还没有介绍" }}</p>
            <div class="meta"><span>{{ world.novel_count }} 本小说</span></div>
          </div>
        </article>
      </div>
    </section>

    <section v-else-if="section === 'world'">
      <p v-if="linkedWorldCards.length === 0" class="empty">还没有关联世界。</p>
      <div class="book-shelf">
        <article v-for="world in linkedWorldCards" :key="world.id" class="resource-card" @click="router.push(resourcePath('worlds', world.id))">
          <img class="book-cover" :src="coverSrc(world.cover_url, 'world')" alt="" />
          <div class="book-copy">
            <h2>{{ world.name }}</h2>
            <p class="summary">{{ world.summary || "还没有介绍" }}</p>
            <div class="meta"><span>{{ world.novel_count }} 本小说</span></div>
          </div>
          <div class="card-menu" @click.stop>
            <button class="icon-button" type="button" aria-label="世界设置" @click="menuKey = menuKey === world.id ? '' : world.id">⋯</button>
            <div v-if="menuKey === world.id" class="menu-list">
              <button class="danger" type="button" @click="unlinkWorld(world.id)">解除关联</button>
            </div>
          </div>
        </article>
      </div>
    </section>

    <section v-else-if="section === 'characters'">
      <p v-if="linkedCharacterCards.length === 0" class="empty">还没有关联角色。</p>
      <div class="book-shelf">
        <article v-for="row in linkedCharacterCards" :key="row.id" class="resource-card" @click="router.push(resourcePath('characters', row.id))">
          <img class="book-cover" :src="coverSrc(row.cover_url, 'character')" alt="" />
          <div class="book-copy">
            <h2>{{ row.name }}</h2>
            <p class="summary">{{ row.summary || "还没有介绍" }}</p>
            <div class="meta"><span>{{ row.novel_count }} 本小说</span></div>
          </div>
          <div class="card-menu" @click.stop>
            <button class="icon-button" type="button" aria-label="角色设置" @click="menuKey = menuKey === row.id ? '' : row.id">⋯</button>
            <div v-if="menuKey === row.id" class="menu-list">
              <button class="danger" type="button" @click="unlinkCharacter(row.id)">解除关联</button>
            </div>
          </div>
        </article>
      </div>
    </section>

    <section v-else-if="section === 'articles'">
      <article v-for="chapter in novel.chapters" :key="chapter.id" class="chapter-line" @click="router.push(`/write/${novel.id}/${chapter.id}`)">
        <div>
          <strong>{{ chapter.title }}</strong>
          <div class="meta"><span>{{ chapter.word_count }} 字</span></div>
        </div>
        <p class="chapter-excerpt">{{ chapter.excerpt || "还没有正文" }}</p>
        <div class="card-menu" @click.stop>
          <button class="icon-button" type="button" aria-label="章节设置" @click="menuKey = menuKey === chapter.id ? '' : chapter.id">⋯</button>
          <div v-if="menuKey === chapter.id" class="menu-list">
            <button class="danger" type="button" @click="removeChapter(chapter)">删除</button>
          </div>
        </div>
      </article>
    </section>

    <section v-else-if="section === 'outline'" class="outline-layout">
      <div>
        <p v-if="nodes.length === 0" class="empty">还没有大纲。可以从一个节点开始，也可以先看右侧的建议。</p>
        <article
          v-for="node in visibleNodes"
          :key="node.id"
          class="outline-node"
          :style="{ marginLeft: `${depth(node) * 16}px` }"
          draggable="true"
          @dragstart="onDragStart(node.id)"
          @dragend="onDragEnd"
          @dragover.prevent
          @drop="onDrop(node)"
          @click="openNode(node)"
        >
          <button v-if="hasChildren(node.id)" class="fold" type="button" :aria-label="collapsed.has(node.id) ? '展开' : '折叠'" @click.stop="toggleFold(node.id)">{{ collapsed.has(node.id) ? "▸" : "▾" }}</button>
          <span v-else class="fold"></span>
          <div>
            <strong>{{ node.title }}</strong>
            <div class="meta">
              <span>{{ labelOf(outlineStatus, node.status) }}</span>
              <span v-if="node.chapter_id">已对应章节</span>
            </div>
            <p v-if="node.content" class="chapter-excerpt">{{ node.content }}</p>
          </div>
          <div class="card-menu" @click.stop>
            <button class="icon-button" type="button" aria-label="大纲设置" @click="menuKey = menuKey === node.id ? '' : node.id">⋯</button>
            <div v-if="menuKey === node.id" class="menu-list">
              <button type="button" @click="moveNode(node, 'up')">上移</button>
              <button type="button" @click="moveNode(node, 'down')">下移</button>
              <button type="button" @click="addNode(node.id)">子节点</button>
              <button type="button" @click="expandNode(node)">扩展建议</button>
              <button type="button" @click="toChapter(node)">{{ node.chapter_id ? "打开章节" : "转为章节" }}</button>
              <button class="danger" type="button" @click="removeNode(node)">删除</button>
            </div>
          </div>
        </article>
      </div>
      <aside class="panel pin-side">
        <strong>AI 建议</strong>
        <p class="muted">建议先展示出来。确认后才会写入这本小说的大纲。</p>
        <NInput v-model:value="instruction" type="textarea" placeholder="想让大纲往哪边发展" :autosize="{ minRows: 2, maxRows: 4 }" />
        <div class="actions" style="margin-top: 10px">
          <NButton size="small" @click="askOutline">生成建议</NButton>
          <NButton size="small" @click="checkOutline">检查大纲</NButton>
        </div>
        <p v-if="outlineReport" class="suggestion">{{ outlineReport }}</p>
        <div v-if="draft" style="margin-top: 12px">
          <p class="meta">{{ draftProvider === "demo" ? "本地示例" : "模型" }}</p>
          <p v-for="item in draft" :key="item.title">{{ item.title }}：{{ item.content }}</p>
          <div class="actions">
            <NButton size="small" type="primary" @click="acceptDraft">确认写入</NButton>
            <NButton size="small" @click="draft = null">放弃</NButton>
          </div>
        </div>
      </aside>
    </section>

    <section v-else-if="section === 'foreshadows'" class="outline-layout">
      <div>
      <article v-for="row in foreshadows" :key="row.id" class="card row-card" @click="editForeshadow(row)">
        <div>
          <strong>{{ row.name }}</strong>
          <div class="meta">
            <span>{{ labelOf(foreshadowStatus, row.status) }}</span>
            <span>{{ labelOf(importanceOptions, row.importance) }}</span>
            <span v-if="row.kind">{{ row.kind }}</span>
          </div>
          <p v-if="row.content" class="chapter-excerpt">{{ row.content }}</p>
        </div>
        <NButton size="small" quaternary @click.stop="removeForeshadow(row)">删除</NButton>
      </article>
      <p v-if="foreshadows.length === 0" class="empty">没有符合筛选的伏笔。</p>
      </div>
      <aside class="panel pin-side">
        <strong>AI 建议</strong>
        <p class="muted">确认前只放进新建窗口，不会直接改正式伏笔。</p>
        <NInput v-model:value="foreshadowHint" type="textarea" placeholder="想补一条什么样的伏笔" :autosize="{ minRows: 2, maxRows: 4 }" />
        <div class="actions" style="margin-top: 10px">
          <NButton size="small" @click="askForeshadow">根据本书生成一条建议</NButton>
          <NButton size="small" @click="reviewForeshadows('forgotten')">检查遗忘</NButton>
          <NButton size="small" @click="reviewForeshadows('payoff')">检查回收</NButton>
          <NButton size="small" @click="reviewForeshadows('conflict')">检查冲突</NButton>
        </div>
        <article v-if="foreshadowReviewReport" class="card" style="padding: 12px; margin-top: 10px">
          <p>{{ foreshadowReviewReport }}</p>
          <p v-for="item in foreshadowReview" :key="item.foreshadow_id">{{ item.name }}：{{ item.reason }}</p>
          <div class="actions">
            <NButton size="small" type="primary" @click="acceptReview">确认</NButton>
            <NButton size="small" @click="foreshadowReview = []; foreshadowReviewReport = ''">放弃</NButton>
          </div>
        </article>
        <article v-if="foreshadowDraft" class="card" style="padding: 12px; margin-top: 10px">
          <strong>{{ foreshadowDraft.name }}</strong>
          <p>{{ foreshadowDraft.content }}</p>
          <div class="actions">
            <NButton size="small" type="primary" @click="acceptForeshadowDraft">放进表单</NButton>
            <NButton size="small" @click="foreshadowDraft = null">放弃</NButton>
          </div>
        </article>
      </aside>
    </section>

    <NModal v-model:show="worldCreateOpen" preset="card" title="创建并关联" style="width: 640px">
      <NForm label-placement="top">
        <NFormItem label="名称"><NInput v-model:value="worldForm.name" /></NFormItem>
        <NFormItem label="介绍"><NInput v-model:value="worldForm.summary" type="textarea" :autosize="{ minRows: 3, maxRows: 5 }" /></NFormItem>
        <NFormItem label="图片"><CoverField v-model="worldForm.cover_url" :choices="worldCovers" owner-kind="world" /></NFormItem>
      </NForm>
      <template #footer>
        <NButton type="primary" @click="saveCreateWorld">保存</NButton>
      </template>
    </NModal>

    <NModal v-model:show="characterCreateOpen" preset="card" title="创建并关联" style="width: 640px">
      <NForm label-placement="top">
        <NFormItem label="姓名"><NInput v-model:value="characterForm.name" /></NFormItem>
        <NFormItem label="基础介绍"><NInput v-model:value="characterForm.summary" type="textarea" :autosize="{ minRows: 3, maxRows: 5 }" /></NFormItem>
        <NFormItem label="图片"><CoverField v-model="characterForm.cover_url" :choices="characterCovers" owner-kind="character" /></NFormItem>
      </NForm>
      <template #footer>
        <NButton type="primary" @click="saveCreateCharacter">保存</NButton>
      </template>
    </NModal>

    <NModal v-model:show="foreshadowOpen" preset="card" :title="foreshadowForm.id ? '编辑伏笔' : '新建伏笔'" style="width: 520px">
      <NForm label-placement="top">
        <NFormItem label="名称"><NInput v-model:value="foreshadowForm.name" /></NFormItem>
        <NFormItem label="内容"><NInput v-model:value="foreshadowForm.content" type="textarea" :autosize="{ minRows: 3, maxRows: 5 }" /></NFormItem>
        <div class="form-row">
          <NFormItem label="重要程度"><NSelect v-model:value="foreshadowForm.importance" :options="importanceOptions" /></NFormItem>
          <NFormItem label="状态"><NSelect v-model:value="foreshadowForm.status" :options="foreshadowStatus" /></NFormItem>
        </div>
        <NFormItem label="类型"><NInput v-model:value="foreshadowForm.kind" placeholder="人物、物品、事件或设定" /></NFormItem>
        <button class="text-button" type="button" @click="foreshadowMore = !foreshadowMore">{{ foreshadowMore ? "收起" : "更多" }}</button>
        <template v-if="foreshadowMore">
          <NFormItem label="关联角色"><NSelect v-model:value="foreshadowForm.character_ids" multiple :options="linkedCharacterOptions" placeholder="本书正在使用的角色" /></NFormItem>
          <NFormItem label="关联大纲"><NSelect v-model:value="foreshadowForm.outline_node_id" clearable :options="nodeOptions" /></NFormItem>
          <NFormItem label="埋下位置"><NSelect v-model:value="foreshadowForm.plant_chapter_id" clearable :options="chapterOptions" /></NFormItem>
          <NFormItem v-if="foreshadowForm.source_quote" label="原文">
            <p class="summary">{{ foreshadowForm.source_quote }}</p>
            <NButton size="small" @click="jumpForeshadow(foreshadowForm)">回到原文</NButton>
          </NFormItem>
          <NFormItem label="预计回收"><NSelect v-model:value="foreshadowForm.expected_chapter_id" clearable :options="chapterOptions" /></NFormItem>
          <NFormItem label="实际回收"><NSelect v-model:value="foreshadowForm.actual_chapter_id" clearable :options="chapterOptions" /></NFormItem>
          <NFormItem label="备注"><NInput v-model:value="foreshadowForm.notes" type="textarea" :autosize="{ minRows: 2, maxRows: 4 }" /></NFormItem>
        </template>
      </NForm>
      <template #footer>
        <NButton type="primary" @click="saveForeshadow">保存</NButton>
      </template>
    </NModal>
  </main>
</template>
