<script setup lang="ts">
import { NButton, NForm, NFormItem, NInput, NSelect, useDialog, useMessage } from "naive-ui"
import { computed, reactive, ref, watch } from "vue"
import { useRoute, useRouter } from "vue-router"
import { api } from "../api"
import type { ChapterBrief, Character, Foreshadow, NovelDetail, OutlineDraftNode, OutlineNode, World } from "../types"

const route = useRoute()
const router = useRouter()
const message = useMessage()
const dialog = useDialog()
const novel = ref<NovelDetail | null>(null)
const worlds = ref<World[]>([])
const allCharacters = ref<Character[]>([])
const linkedCharacterIds = ref<string[]>([])
const newCharacterName = ref("")
const nodes = ref<OutlineNode[]>([])
const foreshadows = ref<Foreshadow[]>([])
const worldIds = ref<string[]>([])
const newWorldName = ref("")
const treeOpen = ref(localStorage.getItem("sf-outline-tree") !== "0")
const aiOpen = ref(localStorage.getItem("sf-outline-ai") !== "0")
const outlineForm = reactive({ id: "", parent_id: null as string | null, world_id: null as string | null, title: "", content: "", notes: "", status: "pending", character_ids: [] as string[] })
const outlineReport = ref("")
const outlineOpen = ref(false)
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

const novelId = computed(() => String(route.params.novelId))
const section = computed(() => String(route.params.section || "articles"))
const chapterOptions = computed(() => (novel.value?.chapters ?? []).map((chapter) => ({ label: chapter.title, value: chapter.id })))
const nodeOptions = computed(() => nodes.value.map((node) => ({ label: node.title, value: node.id })))
const worldOptions = computed(() => worlds.value.map((world) => ({ label: world.name, value: world.id })))
const characterOptions = computed(() => allCharacters.value.map((row) => ({ label: row.name, value: row.id })))
const linkedCharacterOptions = computed(() => (novel.value?.characters ?? []).map((row) => ({ label: row.name, value: row.id })))
const linkedWorldOptions = computed(() => (novel.value?.worlds ?? []).map((row) => ({ label: row.name, value: row.id })))
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
  if (section.value === "world") worlds.value = await api.worlds()
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

async function saveWorldLink() {
  if (!novel.value) return
  await api.updateNovel(novel.value.id, { world_ids: worldIds.value })
  message.success("已更新世界关联，解除关联不会删除世界")
  await load()
}

async function saveCharacterLinks() {
  if (!novel.value) return
  await api.updateNovel(novel.value.id, { character_ids: linkedCharacterIds.value })
  message.success("已更新关联。解除关联不会删除全局角色。")
  await load()
}

async function createLinkedCharacter() {
  if (!newCharacterName.value.trim()) return
  const created = await api.createCharacter({ name: newCharacterName.value.trim(), summary: "" })
  newCharacterName.value = ""
  linkedCharacterIds.value = [...linkedCharacterIds.value, created.id]
  await saveCharacterLinks()
}

async function createLinkedWorld() {
  if (!newWorldName.value.trim() || !novel.value) return
  const world = await api.createWorld({ name: newWorldName.value.trim(), summary: "" })
  worldIds.value = [...worldIds.value, world.id]
  newWorldName.value = ""
  await saveWorldLink()
}

async function addChapter() {
  if (!novel.value) return
  await api.createChapter(novel.value.id, `第${novel.value.chapters.length + 1}章`)
  await load()
}

async function moveChapter(chapter: ChapterBrief, direction: "up" | "down") {
  const rows = await api.moveChapter(chapter.id, direction)
  if (novel.value) {
    novel.value.chapters = rows.map((row) => ({
      id: row.id,
      title: row.title,
      position: row.position,
      word_count: row.word_count,
      volume_id: row.volume_id,
      updated_at: row.updated_at,
    }))
  }
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

function openOutline(parentId: string | null, node?: OutlineNode) {
  Object.assign(outlineForm, {
    id: node?.id ?? "",
    parent_id: node ? node.parent_id : parentId,
    world_id: node?.world_id ?? null,
    title: node?.title ?? "",
    content: node?.content ?? "",
    notes: node?.notes ?? "",
    status: node?.status ?? "pending",
    character_ids: node?.character_ids ?? [],
  })
  outlineOpen.value = true
}

async function saveOutline() {
  if (!outlineForm.title.trim()) return
  const body = {
    title: outlineForm.title,
    content: outlineForm.content,
    notes: outlineForm.notes,
    status: outlineForm.status,
    parent_id: outlineForm.parent_id,
    clear_parent: outlineForm.parent_id === null,
    world_id: outlineForm.world_id,
    clear_world: outlineForm.world_id === null,
    character_ids: outlineForm.character_ids,
  }
  if (outlineForm.id) await api.updateOutline(outlineForm.id, body)
  else await api.createOutline(novelId.value, body)
  outlineOpen.value = false
  nodes.value = await api.outline(novelId.value)
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

async function expandNode(node: OutlineNode) {
  const result = await api.expandOutline(node.id)
  outlineReport.value = result.content
  outlineForm.id = node.id
  outlineForm.title = node.title
  outlineForm.content = result.content
  outlineForm.notes = node.notes
  outlineForm.status = node.status
  outlineForm.parent_id = node.parent_id
  outlineForm.world_id = node.world_id
  outlineForm.character_ids = node.character_ids
  outlineOpen.value = true
  message.info("扩展建议已放进表单，保存后才会写入")
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

function blankForeshadow() {
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
}

function editForeshadow(row: Foreshadow) {
  Object.assign(foreshadowForm, row)
}

async function saveForeshadow() {
  if (!foreshadowForm.name.trim()) {
    message.warning("请填写伏笔名称")
    return
  }
  const body = { ...foreshadowForm }
  if (foreshadowForm.id) await api.updateForeshadow(foreshadowForm.id, body)
  else await api.createForeshadow(novelId.value, body)
  blankForeshadow()
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
  const result = await api.draftForeshadow(novelId.value, instruction.value)
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
  blankForeshadow()
  Object.assign(foreshadowForm, foreshadowDraft.value)
  foreshadowDraft.value = null
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
  worldIds.value = worldIds.value.filter((item) => item !== id)
  await saveWorldLink()
}

async function unlinkCharacter(id: string) {
  linkedCharacterIds.value = linkedCharacterIds.value.filter((item) => item !== id)
  await saveCharacterLinks()
}

watch(treeOpen, (open) => localStorage.setItem("sf-outline-tree", open ? "1" : "0"))
watch(aiOpen, (open) => localStorage.setItem("sf-outline-ai", open ? "1" : "0"))

watch(() => [novelId.value, section.value, filterStatus.value, filterImportance.value], () => {
  void load().catch((error: unknown) => {
    message.error(error instanceof Error ? error.message : "加载失败")
    void router.push("/")
  })
}, { immediate: true })
</script>

<template>
  <main class="page" v-if="novel">
    <header class="workspace-head">
      <div>
        <h1>{{ sectionTitle(section) }}</h1>
        <p class="muted">{{ novel.title }}</p>
      </div>
    </header>

    <section v-if="section === 'overview'" class="stats">
      <article class="card stat"><strong>{{ novel.chapter_count }}</strong><span>章节</span></article>
      <article class="card stat"><strong>{{ novel.word_count }}</strong><span>字</span></article>
      <article class="card stat"><strong>{{ novel.worlds.length }}</strong><span>关联世界</span></article>
      <article class="card stat"><strong>{{ novel.characters.length }}</strong><span>关联角色</span></article>
      <article class="card library-card">
        <p>{{ novel.summary || "还没有简介" }}</p>
        <p class="muted">{{ novel.worlds.map((row) => row.name).join("、") || "还没有关联世界" }}</p>
      </article>
    </section>

    <section v-else-if="section === 'world'">
      <article v-for="world in novel.worlds" :key="world.id" class="card row-card">
        <strong>{{ world.name }}</strong>
        <div class="actions">
          <NButton size="small" type="primary" @click="router.push(resourcePath('worlds', world.id))">查看</NButton>
          <NButton size="small" quaternary @click="unlinkWorld(world.id)">解除关联</NButton>
        </div>
      </article>
      <div class="panel" style="padding: 18px">
        <NFormItem label="添加已有世界">
          <NSelect v-model:value="worldIds" multiple :options="worldOptions" placeholder="可以从世界库关联多个世界" />
        </NFormItem>
        <NButton type="primary" @click="saveWorldLink">保存关联</NButton>
        <p class="muted">解除关联不会删除世界。多个小说可以关联同一个世界。</p>
        <div class="actions" style="margin-top: 16px">
          <NInput v-model:value="newWorldName" placeholder="新建全局世界并关联到本书" style="max-width: 280px" />
          <NButton @click="createLinkedWorld">创建并关联</NButton>
        </div>
      </div>
    </section>

    <section v-else-if="section === 'characters'">
      <article v-for="row in novel.characters" :key="row.id" class="card row-card">
        <strong>{{ row.name }}</strong>
        <div class="actions">
          <NButton size="small" type="primary" @click="router.push(resourcePath('characters', row.id))">查看</NButton>
          <NButton size="small" quaternary @click="unlinkCharacter(row.id)">解除关联</NButton>
        </div>
      </article>
      <div class="panel" style="padding: 18px">
        <NFormItem label="添加已有角色">
          <NSelect v-model:value="linkedCharacterIds" multiple :options="characterOptions" placeholder="可以从全局角色库关联" />
        </NFormItem>
        <NButton type="primary" @click="saveCharacterLinks">保存关联</NButton>
        <p class="muted">解除关联不会删除角色库里的档案。时期、专属版本和关系图留在后续阶段。</p>
        <div class="actions" style="margin-top: 16px">
          <NInput v-model:value="newCharacterName" placeholder="新建全局角色并关联到本书" style="max-width: 280px" />
          <NButton @click="createLinkedCharacter">创建并关联</NButton>
        </div>
      </div>
    </section>

    <section v-else-if="section === 'articles'">
      <div class="section-title">
        <strong>章节</strong>
        <NButton size="small" @click="addChapter">新增章节</NButton>
      </div>
      <article v-for="chapter in novel.chapters" :key="chapter.id" class="card row-card">
        <div>
          <strong>{{ chapter.title }}</strong>
          <div class="meta"><span>第 {{ chapter.position }} 章</span><span>{{ chapter.word_count }} 字</span></div>
        </div>
        <div class="actions">
          <NButton size="small" quaternary @click="moveChapter(chapter, 'up')">上移</NButton>
          <NButton size="small" quaternary @click="moveChapter(chapter, 'down')">下移</NButton>
          <NButton size="small" type="primary" @click="router.push(`/write/${novel.id}/${chapter.id}`)">写作</NButton>
          <NButton size="small" quaternary @click="removeChapter(chapter)">删除</NButton>
        </div>
      </article>
    </section>

    <section v-else-if="section === 'outline'">
      <div class="section-title">
        <button class="text-button" type="button" @click="treeOpen = !treeOpen"><strong>树状大纲 {{ treeOpen ? "−" : "+" }}</strong></button>
        <NButton size="small" @click="openOutline(null)">添加节点</NButton>
      </div>
      <p v-if="treeOpen && nodes.length === 0" class="empty">还没有大纲。可以从一个节点开始，也可以先看 AI 建议。</p>
      <template v-if="treeOpen">
      <article
        v-for="node in orderedNodes"
        :key="node.id"
        class="card row-card"
        :style="{ marginLeft: `${depth(node) * 22}px` }"
        draggable="true"
        @dragstart="onDragStart(node.id)"
        @dragover.prevent
        @drop="onDrop(node)"
      >
        <div>
          <strong>{{ node.title }}</strong>
          <div class="meta">
            <span>{{ labelOf(outlineStatus, node.status) }}</span>
            <span v-if="node.chapter_id">已对应章节</span>
            <button v-if="node.world_id" class="text-button" type="button" @click="router.push(resourcePath('worlds', node.world_id))">{{ linkedWorldOptions.find((item) => item.value === node.world_id)?.label || "世界" }}</button>
            <button v-for="characterId in node.character_ids" :key="characterId" class="text-button" type="button" @click="router.push(resourcePath('characters', characterId))">{{ linkedCharacterOptions.find((item) => item.value === characterId)?.label || "角色" }}</button>
          </div>
          <p v-if="node.content" class="summary">{{ node.content }}</p>
        </div>
        <div class="actions">
          <NButton size="small" quaternary @click="moveNode(node, 'up')">上移</NButton>
          <NButton size="small" quaternary @click="moveNode(node, 'down')">下移</NButton>
          <NButton size="small" @click="openOutline(node.id)">子节点</NButton>
          <NButton size="small" @click="openOutline(null, node)">编辑</NButton>
          <NButton size="small" @click="expandNode(node)">扩展建议</NButton>
          <NButton size="small" @click="toChapter(node)">{{ node.chapter_id ? "打开章节" : "转为章节" }}</NButton>
          <NButton size="small" quaternary @click="removeNode(node)">删除</NButton>
        </div>
      </article>
      </template>

      <div class="panel" style="padding: 16px; margin-top: 18px">
        <button class="text-button" type="button" @click="aiOpen = !aiOpen"><strong>AI 建议 {{ aiOpen ? "−" : "+" }}</strong></button>
        <div v-show="aiOpen">
        <p class="muted">建议先展示出来。确认后才会写入这本小说的大纲。</p>
        <NInput v-model:value="instruction" type="textarea" placeholder="想让大纲往哪边发展" :autosize="{ minRows: 2, maxRows: 4 }" />
        <div class="actions" style="margin-top: 10px">
          <NButton size="small" @click="askOutline">生成建议</NButton>
          <NButton size="small" @click="checkOutline">检查大纲</NButton>
        </div>
        <p v-if="outlineReport" class="suggestion">{{ outlineReport }}</p>
        <div v-if="draft" style="margin-top: 12px">
          <p class="meta">{{ draftProvider === "demo" ? "本地示例" : "模型" }}</p>
          <ul>
            <li v-for="item in draft" :key="item.title">{{ item.title }}：{{ item.content }}</li>
          </ul>
          <div class="actions">
            <NButton size="small" type="primary" @click="acceptDraft">确认写入</NButton>
            <NButton size="small" @click="draft = null">放弃</NButton>
          </div>
        </div>
        </div>
      </div>

      <div v-if="outlineOpen" class="panel" style="padding: 16px; margin-top: 18px">
        <NForm label-placement="top">
          <NFormItem label="标题"><NInput v-model:value="outlineForm.title" /></NFormItem>
          <NFormItem label="内容"><NInput v-model:value="outlineForm.content" type="textarea" :autosize="{ minRows: 3, maxRows: 6 }" /></NFormItem>
          <NFormItem label="备注"><NInput v-model:value="outlineForm.notes" /></NFormItem>
          <NFormItem label="状态"><NSelect v-model:value="outlineForm.status" :options="outlineStatus" /></NFormItem>
          <p class="muted">地点和事件还没有独立档案，这一阶段只能关联本书正在使用的角色和世界。</p>
          <NFormItem label="关联世界"><NSelect v-model:value="outlineForm.world_id" clearable :options="linkedWorldOptions" placeholder="只显示本书正在使用的世界" /></NFormItem>
          <NFormItem label="关联角色"><NSelect v-model:value="outlineForm.character_ids" multiple :options="linkedCharacterOptions" placeholder="只显示本书正在使用的角色" /></NFormItem>
        </NForm>
        <NButton type="primary" @click="saveOutline">保存节点</NButton>
      </div>
    </section>

    <section v-else-if="section === 'foreshadows'" class="split">
      <div>
        <div class="actions" style="margin-bottom: 12px">
          <NSelect v-model:value="filterStatus" clearable :options="foreshadowStatus" placeholder="状态" style="width: 140px" />
          <NSelect v-model:value="filterImportance" clearable :options="importanceOptions" placeholder="重要程度" style="width: 140px" />
          <NButton size="small" @click="blankForeshadow">新建</NButton>
        </div>
        <article v-for="row in foreshadows" :key="row.id" class="card row-card" @click="editForeshadow(row)">
          <div>
            <strong>{{ row.name }}</strong>
            <div class="meta">
              <span>{{ labelOf(foreshadowStatus, row.status) }}</span>
              <span>{{ labelOf(importanceOptions, row.importance) }}</span>
              <span v-if="row.kind">{{ row.kind }}</span>
            </div>
          </div>
          <NButton size="small" quaternary @click.stop="removeForeshadow(row)">删除</NButton>
        </article>
        <p v-if="foreshadows.length === 0" class="empty">没有符合筛选的伏笔。</p>
      </div>
      <div class="panel" style="padding: 16px">
        <NForm label-placement="top">
          <NFormItem label="名称"><NInput v-model:value="foreshadowForm.name" /></NFormItem>
          <NFormItem label="内容"><NInput v-model:value="foreshadowForm.content" type="textarea" :autosize="{ minRows: 3, maxRows: 6 }" /></NFormItem>
          <NFormItem label="类型"><NInput v-model:value="foreshadowForm.kind" placeholder="人物、物品、事件或设定" /></NFormItem>
          <NFormItem label="重要程度"><NSelect v-model:value="foreshadowForm.importance" :options="importanceOptions" /></NFormItem>
          <NFormItem label="状态"><NSelect v-model:value="foreshadowForm.status" :options="foreshadowStatus" /></NFormItem>
          <NFormItem label="关联角色"><NSelect v-model:value="foreshadowForm.character_ids" multiple :options="linkedCharacterOptions" placeholder="只显示本书正在使用的角色" /></NFormItem>
          <NFormItem label="关联大纲"><NSelect v-model:value="foreshadowForm.outline_node_id" clearable :options="nodeOptions" /></NFormItem>
          <NFormItem label="埋下位置"><NSelect v-model:value="foreshadowForm.plant_chapter_id" clearable :options="chapterOptions" /></NFormItem>
          <NFormItem v-if="foreshadowForm.source_quote" label="原文">
            <p class="summary">{{ foreshadowForm.source_quote }}</p>
            <NButton size="small" @click="jumpForeshadow(foreshadowForm)">回到原文</NButton>
          </NFormItem>
          <NFormItem label="预计回收"><NSelect v-model:value="foreshadowForm.expected_chapter_id" clearable :options="chapterOptions" /></NFormItem>
          <NFormItem label="实际回收"><NSelect v-model:value="foreshadowForm.actual_chapter_id" clearable :options="chapterOptions" /></NFormItem>
          <NFormItem label="备注"><NInput v-model:value="foreshadowForm.notes" type="textarea" /></NFormItem>
        </NForm>
        <div class="actions">
          <NButton type="primary" @click="saveForeshadow">保存伏笔</NButton>
        </div>
        <div style="margin-top: 18px">
          <strong>AI 建议</strong>
          <p class="muted">确认前只放进表单，不会直接改正式伏笔。</p>
          <NButton size="small" @click="askForeshadow">根据本书生成一条建议</NButton>
          <NButton size="small" @click="reviewForeshadows('forgotten')">检查遗忘</NButton>
          <NButton size="small" @click="reviewForeshadows('payoff')">检查回收</NButton>
          <NButton size="small" @click="reviewForeshadows('conflict')">检查冲突</NButton>
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
        </div>
      </div>
    </section>
  </main>
</template>
