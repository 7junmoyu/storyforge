<script setup lang="ts">
import { BubbleMenu, EditorContent, useEditor } from "@tiptap/vue-3"
import StarterKit from "@tiptap/starter-kit"
import { NButton, NInput, NModal, useDialog, useMessage } from "naive-ui"
import { computed, onBeforeUnmount, ref, watch } from "vue"
import { RouterLink, useRoute, useRouter } from "vue-router"
import { api } from "../api"
import { InkMarks, inkMarkKey, type InkRange } from "../inkMarks"
import type { AiAction, ChapterBrief, NovelDetail, Revision, Suggestion, Volume, World } from "../types"

const route = useRoute()
const router = useRouter()
const message = useMessage()
const dialog = useDialog()
const novel = ref<NovelDetail | null>(null)
const chapters = ref<ChapterBrief[]>([])
const activeId = ref("")
const saveState = ref("已保存")
const suggestion = ref<Suggestion | null>(null)
const asking = ref(false)
const revisions = ref<Revision[]>([])
const showRevisions = ref(false)
const assistOpen = ref(false)
const chaptersOpen = ref(true)
const toolsOpen = ref(false)
const marks = ref<{ id: string; quote: string; start: number; end: number; chapter_id: string }[]>([])
const allMarks = ref<{ id: string; quote: string; start: number; end: number; chapter_id: string }[]>([])
const volumes = ref<Volume[]>([])
const allWorlds = ref<World[]>([])
const collapsedVolumes = ref(new Set<string>())
const volumeMenu = ref("")
const volumeNameOpen = ref(false)
const volumeName = ref("")
const volumePickOpen = ref(false)
const volumePickId = ref("")
const volumePickIds = ref<string[]>([])
const toolMenu = ref(false)
const worldPick = ref(false)
const markMenu = ref("")
const findText = ref("")
const replaceText = ref("")
const range = ref<{ from: number; to: number } | null>(null)
let savedHtml = ""
let hydrating = false
let timer = 0

const actions: { key: AiAction; label: string }[] = [
  { key: "continue", label: "续写" },
  { key: "expand", label: "扩写" },
  { key: "polish", label: "润色" },
  { key: "rewrite", label: "改写" },
  { key: "shorten", label: "缩写" },
  { key: "style", label: "文风" },
  { key: "dialogue", label: "对话" },
]
const analysis: { key: AiAction; label: string }[] = [
  { key: "character", label: "人物行为" },
  { key: "plot", label: "剧情逻辑" },
  { key: "conflict", label: "设定冲突" },
]
const writingActions = new Set<AiAction>(["continue", "expand", "polish", "rewrite", "shorten", "style", "dialogue"])

const editor = useEditor({
  content: "<p></p>",
  extensions: [StarterKit, InkMarks],
  onUpdate: () => {
    if (hydrating) return
    saveState.value = "未保存"
    window.clearTimeout(timer)
    timer = window.setTimeout(() => void persist(), 700)
  },
})

const activeChapter = computed(() => chapters.value.find((item) => item.id === activeId.value) || null)
const chapterWorldName = computed(() => worldNameOf(activeChapter.value?.world_id || ""))

function worldNameOf(id: string) {
  if (!id) return ""
  return allWorlds.value.find((item) => item.id === id)?.name || novel.value?.worlds.find((item) => item.id === id)?.name || ""
}

function marksOf(chapterId: string) {
  return allMarks.value.filter((item) => item.chapter_id === chapterId).sort((a, b) => a.start - b.start)
}

function shortQuote(text: string) {
  return text.replace(/\s+/g, "").slice(0, 4)
}

function emptyVolumeAnchor(volume: Volume) {
  if (volume.position < 100) return volume.position / 1000
  const slot = volume.position - 100
  return Math.floor(slot / 100) + 0.5 + (slot % 100) * 0.01
}

const sidebar = computed(() => {
  const loose = chapters.value.filter((item) => !item.volume_id).sort((a, b) => a.position - b.position)
  const groups = volumes.value.map((volume) => {
    const rows = chapters.value.filter((item) => item.volume_id === volume.id).sort((a, b) => a.position - b.position)
    return { volume, chapters: rows, anchor: rows.length ? rows[0].position : emptyVolumeAnchor(volume) }
  })
  const items: ({ kind: "chapter"; chapter: ChapterBrief; anchor: number } | { kind: "volume"; volume: Volume; chapters: ChapterBrief[]; anchor: number })[] = [
    ...loose.map((chapter) => ({ kind: "chapter" as const, chapter, anchor: chapter.position })),
    ...groups.map((group) => ({ kind: "volume" as const, volume: group.volume, chapters: group.chapters, anchor: group.anchor })),
  ]
  return items.sort((a, b) => a.anchor - b.anchor || (a.kind === "volume" ? -1 : 1))
})

function paragraphs(text: string) {
  return text
    .split(/\n+/)
    .map((line) => `<p>${line.replace(/&/g, "&amp;").replace(/</g, "&lt;").replace(/>/g, "&gt;") || "<br>"}</p>`)
    .join("")
}

async function loadNovel() {
  const detail = await api.novel(String(route.params.novelId))
  novel.value = detail
  chapters.value = detail.chapters
  volumes.value = await api.volumes(detail.id)
  allMarks.value = await api.novelMarks(detail.id)
  allWorlds.value = await api.worlds()
  const requested = String(route.params.chapterId || "")
  const next = chapters.value.find((item) => item.id === requested)?.id ?? chapters.value[0]?.id
  if (next) await openChapter(next)
}

async function openChapter(id: string) {
  if (activeId.value && activeId.value !== id) await persist()
  const chapter = await api.chapter(id)
  activeId.value = chapter.id
  marks.value = await api.marks(chapter.id)
  hydrating = true
  editor.value?.commands.setContent(chapter.content || "<p></p>", false)
  hydrating = false
  savedHtml = editor.value?.getHTML() ?? chapter.content
  if (String(route.params.chapterId) === chapter.id) applyQuerySelection()
  paintMarks()
  saveState.value = "已保存"
  suggestion.value = null
  showRevisions.value = false
  if (route.params.chapterId !== chapter.id && novel.value) {
    await router.replace(`/write/${novel.value.id}/${chapter.id}`)
  }
}

async function persist() {
  if (!activeId.value || !editor.value) return
  const html = editor.value.getHTML()
  if (html === savedHtml) {
    saveState.value = "已保存"
    return
  }
  saveState.value = "保存中"
  try {
    const updated = await api.updateChapter(activeId.value, { content: html })
    savedHtml = updated.content
    saveState.value = "已保存"
    const brief = chapters.value.find((item) => item.id === updated.id)
    if (brief) brief.word_count = updated.word_count
  } catch (error) {
    saveState.value = "保存失败"
    message.error(error instanceof Error ? error.message : "保存失败")
  }
}

async function rename(chapter: ChapterBrief) {
  const next = chapter.title.trim()
  if (!next) return
  const updated = await api.updateChapter(chapter.id, { title: next })
  chapter.title = updated.title
}

async function addChapter() {
  if (!novel.value) return
  const created = await api.createChapter(novel.value.id, `第${chapters.value.length + 1}章`)
  chapters.value.push({
    id: created.id,
    title: created.title,
    position: created.position,
    word_count: 0,
    volume_id: created.volume_id,
    world_id: created.world_id,
    updated_at: created.updated_at,
  })
  await openChapter(created.id)
}

function defaultVolumeTitle() {
  return `第${volumes.value.length + 1}卷`
}

function openVolumeName() {
  volumeName.value = ""
  volumeNameOpen.value = true
}

async function confirmVolumeName(useDefault: boolean) {
  if (!novel.value) return
  const typed = volumeName.value.trim()
  if (!useDefault && !typed) return
  const title = useDefault || !typed ? defaultVolumeTitle() : typed
  volumeNameOpen.value = false
  let created = await api.createVolume(novel.value.id, title)
  const unplaced = volumes.value.filter((item) => item.position < 100).map((item) => item.position)
  const position = unplaced.length ? Math.min(...unplaced) - 1 : 0
  if (created.position !== position) created = await api.updateVolume(novel.value.id, created.id, { position })
  volumes.value.push(created)
}

function filledChapterIds(ids: string[]) {
  const chosen = chapters.value.filter((item) => ids.includes(item.id))
  if (chosen.length === 0) return []
  const min = Math.min(...chosen.map((item) => item.position))
  const max = Math.max(...chosen.map((item) => item.position))
  return chapters.value.filter((item) => item.position >= min && item.position <= max).map((item) => item.id)
}

function paintMarks() {
  const view = editor.value?.view
  if (!view) return
  const ranges: InkRange[] = marksOf(activeId.value).map((item) => ({ start: item.start, end: item.end }))
  view.dispatch(view.state.tr.setMeta(inkMarkKey, ranges))
}

function toggleVolume(id: string) {
  const next = new Set(collapsedVolumes.value)
  if (next.has(id)) next.delete(id)
  else next.add(id)
  collapsedVolumes.value = next
}

function dragKind(event: DragEvent) {
  return event.dataTransfer?.getData("text/plain") || ""
}

function onListDrop(event: DragEvent) {
  const data = dragKind(event)
  if (!data.startsWith("volume:")) return
  void placeEmptyVolume(data.slice(7), null)
}

function onVolumeBlockDrop(volumeId: string, event: DragEvent) {
  const data = dragKind(event)
  if (data.startsWith("volume:")) {
    event.stopPropagation()
    void placeEmptyVolume(data.slice(7), `volume:${volumeId}`)
    return
  }
  if (data.startsWith("chapter:")) {
    event.stopPropagation()
    void dropOnVolume(volumeId, data.slice(8))
  }
}

function onChapterDrop(chapterId: string, event: DragEvent) {
  const data = dragKind(event)
  if (!data.startsWith("volume:")) return
  event.stopPropagation()
  void placeEmptyVolume(data.slice(7), `chapter:${chapterId}`)
}

function onChapterDrag(id: string, event: DragEvent) {
  event.stopPropagation()
  event.dataTransfer?.setData("text/plain", `chapter:${id}`)
}

function onVolumeDrag(id: string, event: DragEvent) {
  event.stopPropagation()
  event.dataTransfer?.setData("text/plain", `volume:${id}`)
  if (event.dataTransfer) event.dataTransfer.effectAllowed = "move"
}

async function placeEmptyVolume(volumeId: string, before: string | null) {
  if (!novel.value) return
  const moving = sidebar.value.find((block) => block.kind === "volume" && block.volume.id === volumeId && block.chapters.length === 0)
  if (!moving || moving.kind !== "volume") return
  if (before === `volume:${volumeId}`) return
  const rest = sidebar.value.filter((block) => !(block.kind === "volume" && block.volume.id === volumeId && block.chapters.length === 0))
  let index = rest.length
  if (before) {
    const found = rest.findIndex((block) =>
      before.startsWith("chapter:")
        ? block.kind === "chapter" && block.chapter.id === before.slice(8)
        : block.kind === "volume" && block.volume.id === before.slice(7),
    )
    if (found >= 0) index = found
  }
  rest.splice(index, 0, moving)
  let previous = 0
  let gap = 0
  for (const block of rest) {
    if (block.kind === "chapter") {
      previous = block.chapter.position
      gap = 0
      continue
    }
    if (block.chapters.length === 0) {
      const position = 100 + previous * 100 + gap
      gap += 1
      if (block.volume.position !== position) {
        const updated = await api.updateVolume(novel.value.id, block.volume.id, { position })
        block.volume.position = updated.position
      }
      continue
    }
    const last = block.chapters[block.chapters.length - 1]
    if (last) {
      previous = last.position
      gap = 0
    }
  }
}

async function dropOnVolume(volumeId: string, chapterId: string) {
  const members = chapters.value.filter((item) => item.volume_id === volumeId || item.id === chapterId)
  if (members.length === 0) return
  const min = Math.min(...members.map((item) => item.position))
  const max = Math.max(...members.map((item) => item.position))
  const targets = chapters.value.filter((item) => item.position >= min && item.position <= max && item.volume_id !== volumeId)
  for (const chapter of targets) {
    const updated = await api.updateChapter(chapter.id, { volume_id: volumeId })
    chapter.volume_id = updated.volume_id
  }
}

async function setVolumeMembers(volumeId: string, ids: string[]) {
  const chosen = new Set(ids)
  for (const chapter of chapters.value) {
    const inside = chapter.volume_id === volumeId
    if (chosen.has(chapter.id) && !inside) {
      const updated = await api.updateChapter(chapter.id, { volume_id: volumeId })
      chapter.volume_id = updated.volume_id
    } else if (!chosen.has(chapter.id) && inside) {
      const updated = await api.updateChapter(chapter.id, { clear_volume: true })
      chapter.volume_id = updated.volume_id
    }
  }
}

function openVolumePick(volume: Volume) {
  volumeMenu.value = ""
  volumePickId.value = volume.id
  volumePickIds.value = filledChapterIds(chapters.value.filter((item) => item.volume_id === volume.id).map((item) => item.id))
  volumePickOpen.value = true
}

function toggleVolumePick(chapterId: string) {
  const next = volumePickIds.value.includes(chapterId)
    ? volumePickIds.value.filter((id) => id !== chapterId)
    : [...volumePickIds.value, chapterId]
  volumePickIds.value = filledChapterIds(next)
}

async function confirmVolumePick() {
  if (!volumePickId.value) return
  const ids = filledChapterIds(volumePickIds.value)
  volumePickOpen.value = false
  await setVolumeMembers(volumePickId.value, ids)
}

async function removeVolume(volume: Volume) {
  if (!novel.value) return
  volumeMenu.value = ""
  await api.deleteVolume(novel.value.id, volume.id)
  volumes.value = volumes.value.filter((item) => item.id !== volume.id)
  for (const chapter of chapters.value) {
    if (chapter.volume_id === volume.id) chapter.volume_id = null
  }
}

async function chooseChapterWorld(worldId: string) {
  if (!activeChapter.value || !novel.value) return
  worldPick.value = false
  const updated = await api.updateChapter(activeChapter.value.id, { world_id: worldId })
  activeChapter.value.world_id = updated.world_id
  if (!novel.value.worlds.some((item) => item.id === worldId)) {
    const world = allWorlds.value.find((item) => item.id === worldId)
    if (world) novel.value.worlds.push({ id: world.id, name: world.name })
  }
}

async function jumpToMark(chapter: ChapterBrief, mark: { start: number; end: number }) {
  markMenu.value = ""
  if (activeId.value !== chapter.id) await openChapter(chapter.id)
  revealMark(mark)
}

function onMarkClick(chapter: ChapterBrief) {
  const rows = marksOf(chapter.id)
  if (rows.length === 0) return
  if (rows.length === 1) {
    void jumpToMark(chapter, rows[0])
    return
  }
  markMenu.value = markMenu.value === chapter.id ? "" : chapter.id
}

function replaceTextInChapter(all: boolean) {
  if (!editor.value || !findText.value) return
  const html = editor.value.getHTML()
  if (!html.includes(findText.value)) {
    message.warning("这一章里没有找到")
    return
  }
  const next = all ? html.split(findText.value).join(replaceText.value) : html.replace(findText.value, replaceText.value)
  editor.value.commands.setContent(next, false)
  void persist()
}

function removeChapter(chapter: ChapterBrief) {
  dialog.warning({
    title: "删除章节",
    content: `删除「${chapter.title}」后不能从工作台恢复。`,
    positiveText: "删除",
    negativeText: "取消",
    onPositiveClick: async () => {
      try {
        await api.deleteChapter(chapter.id)
        chapters.value = chapters.value.filter((item) => item.id !== chapter.id)
        if (activeId.value === chapter.id && chapters.value[0]) await openChapter(chapters.value[0].id)
      } catch (error) {
        message.error(error instanceof Error ? error.message : "删除失败")
      }
    },
  })
}

function selectedRange() {
  if (!editor.value) return null
  const { from, to } = editor.value.state.selection
  if (from === to) return null
  const text = editor.value.state.doc.textBetween(from, to, "\n")
  if (!text.trim()) return null
  return { from, to, text }
}

function applyQuerySelection() {
  if (!editor.value) return
  const from = Number(route.query.from)
  const to = Number(route.query.to)
  if (!Number.isFinite(from) || !Number.isFinite(to) || to <= from) return
  const size = editor.value.state.doc.content.size
  const end = Math.min(to, size)
  const start = Math.min(Math.max(from, 0), end)
  if (end <= start) return
  editor.value.chain().setTextSelection({ from: start, to: end }).scrollIntoView().run()
}

async function markSelection() {
  const picked = selectedRange()
  if (!picked || !activeId.value) return
  const created = await api.createMark(activeId.value, { quote: picked.text, start: picked.from, end: picked.to })
  marks.value = await api.marks(activeId.value)
  allMarks.value = [...allMarks.value.filter((item) => item.chapter_id !== activeId.value), ...marks.value]
  if (!allMarks.value.some((item) => item.id === created.id)) allMarks.value.push({ ...created, chapter_id: activeId.value })
  paintMarks()
  message.success("已记下这段文字和位置")
}

function createCharacterFromSelection() {
  const picked = selectedRange()
  if (!picked || !novel.value) return
  const name = picked.text.trim().slice(0, 40)
  dialog.warning({
    title: "新建角色",
    content: `用「${name}」创建全局角色，并关联到当前小说。取消则不会写入。`,
    positiveText: "创建",
    negativeText: "取消",
    onPositiveClick: async () => {
      const created = await api.createCharacter({ name, summary: "" })
      const ids = [...(novel.value?.characters.map((row) => row.id) ?? []), created.id]
      await api.updateNovel(novel.value!.id, { character_ids: ids })
      novel.value = await api.novel(novel.value!.id)
      message.success("已创建并关联到当前小说")
    },
  })
}

function createForeshadowFromSelection() {
  const picked = selectedRange()
  if (!picked || !novel.value || !activeId.value) return
  const content = picked.text.trim()
  dialog.warning({
    title: "新建伏笔",
    content: "把选中文字记成当前小说的伏笔，并记下这一章和位置。取消则不会写入。",
    positiveText: "创建",
    negativeText: "取消",
    onPositiveClick: async () => {
      await api.createForeshadow(novel.value!.id, {
        name: content.slice(0, 40) || "选区伏笔",
        content,
        status: "planted",
        plant_chapter_id: activeId.value,
        source_quote: content,
        source_start: picked.from,
        source_end: picked.to,
      })
      message.success("已写入本书伏笔")
    },
  })
}

async function copySelection() {
  const picked = selectedRange()
  if (!picked) return
  await navigator.clipboard.writeText(picked.text)
}

function cutSelection() {
  const picked = selectedRange()
  if (!picked || !editor.value) return
  void navigator.clipboard.writeText(picked.text)
  editor.value.chain().focus().deleteSelection().run()
}

function selectAllText() {
  editor.value?.chain().focus().selectAll().run()
}

async function revealMark(mark: { start: number; end: number }) {
  editor.value?.chain().focus().setTextSelection({ from: mark.start, to: mark.end }).scrollIntoView().run()
}

async function removeMark(id: string) {
  await api.deleteMark(id)
  marks.value = marks.value.filter((item) => item.id !== id)
  allMarks.value = allMarks.value.filter((item) => item.id !== id)
  paintMarks()
}

async function ask(action: AiAction) {
  if (!editor.value || !activeId.value) return
  await persist()
  const { from, to } = editor.value.state.selection
  const selected = from === to ? "" : editor.value.state.doc.textBetween(from, to, "\n")
  range.value = { from, to }
  asking.value = true
  suggestion.value = null
  try {
    suggestion.value = await api.suggest(activeId.value, action, selected)
  } catch (error) {
    message.error(error instanceof Error ? error.message : "生成失败")
  } finally {
    asking.value = false
  }
}

async function accept() {
  if (!suggestion.value || !editor.value || !range.value) return
  const current = suggestion.value
  if (!writingActions.has(current.action)) {
    await api.acceptSuggestion(current.id)
    suggestion.value = null
    message.success("已确认分析结果，正文没有改动")
    return
  }
  const html = paragraphs(current.suggestion)
  try {
    const chain = editor.value.chain().focus()
    if (current.action === "continue" && range.value.from === range.value.to) {
      chain.setTextSelection(editor.value.state.doc.content.size).insertContent(html).run()
    } else if (current.action === "continue") {
      chain.setTextSelection(range.value.to).insertContent(html).run()
    } else {
      chain.deleteRange(range.value).insertContent(html).run()
    }
  } catch {
    message.error("正文已经变化，请重新生成建议")
    return
  }
  await api.acceptSuggestion(current.id)
  suggestion.value = null
  await persist()
  message.success("已写入正文")
}

async function reject() {
  if (!suggestion.value) return
  await api.rejectSuggestion(suggestion.value.id)
  suggestion.value = null
}

async function toggleRevisions() {
  showRevisions.value = !showRevisions.value
  if (showRevisions.value && activeId.value) revisions.value = await api.revisions(activeId.value)
}

async function restore(revision: Revision) {
  if (!activeId.value) return
  const chapter = await api.restoreRevision(activeId.value, revision.id)
  hydrating = true
  editor.value?.commands.setContent(chapter.content || "<p></p>", false)
  hydrating = false
  savedHtml = editor.value?.getHTML() ?? chapter.content
  const brief = chapters.value.find((item) => item.id === chapter.id)
  if (brief) brief.word_count = chapter.word_count
  revisions.value = await api.revisions(activeId.value)
  message.success("已恢复这个版本")
}

watch(() => [route.params.novelId, route.params.chapterId], () => {
  if (String(route.params.chapterId || "") === activeId.value && novel.value) return
  void loadNovel().catch((error: unknown) => {
    message.error(error instanceof Error ? error.message : "小说不存在")
    void router.push("/")
  })
}, { immediate: true })

onBeforeUnmount(() => {
  window.clearTimeout(timer)
  void persist()
  editor.value?.destroy()
})
</script>

<template>
  <div class="editor-shell" :class="{ 'assist-closed': !assistOpen, 'chapters-closed': !chaptersOpen }" v-if="novel">
    <header class="write-bar">
      <RouterLink class="brand" to="/">
        <strong>StoryForge</strong>
      </RouterLink>
      <RouterLink class="nav-link" :to="`/novels/${novel.id}/articles`">返回文章</RouterLink>
      <span class="muted">{{ novel.title }}</span>
    </header>
    <aside class="side" @click="volumeMenu = ''; markMenu = ''" @dragover.prevent @drop="onListDrop">
      <div class="side-pin">
        <strong>章节</strong>
        <span class="actions">
          <button class="text-button" type="button" @click="openVolumeName">分卷</button>
          <button class="text-button" type="button" @click="addChapter">新增</button>
        </span>
      </div>
      <template v-for="block in sidebar" :key="block.kind === 'volume' ? block.volume.id : block.chapter.id">
        <div
          v-if="block.kind === 'volume'"
          class="volume-block"
          :class="{ 'can-move': block.chapters.length === 0 }"
          :draggable="block.chapters.length === 0"
          @dragstart="onVolumeDrag(block.volume.id, $event)"
          @dragover.prevent
          @drop="onVolumeBlockDrop(block.volume.id, $event)"
        >
          <div class="volume-head">
            <button class="volume-title" type="button" @click="toggleVolume(block.volume.id)">{{ collapsedVolumes.has(block.volume.id) ? "▸" : "▾" }} {{ block.volume.title }}</button>
            <button class="icon-button" type="button" aria-label="分卷设置" @click.stop="volumeMenu = volumeMenu === block.volume.id ? '' : block.volume.id">⋯</button>
            <div v-if="volumeMenu === block.volume.id" class="menu-list" @click.stop>
              <button type="button" @click="openVolumePick(block.volume)">选择章节</button>
              <button class="danger" type="button" @click="removeVolume(block.volume)">删除分卷</button>
            </div>
          </div>
          <template v-if="!collapsedVolumes.has(block.volume.id)">
            <div
              v-for="chapter in block.chapters"
              :key="chapter.id"
              class="chapter-item"
              :class="{ active: chapter.id === activeId }"
              draggable="true"
              @dragstart="onChapterDrag(chapter.id, $event)"
              @dragover.prevent
              @drop="onChapterDrop(chapter.id, $event)"
              @click="openChapter(chapter.id)"
            >
              <strong>{{ chapter.title }}</strong>
              <div class="meta"><span>{{ chapter.word_count }} 字</span><span v-if="worldNameOf(chapter.world_id || '')">{{ worldNameOf(chapter.world_id || '') }}</span></div>
              <div v-if="marksOf(chapter.id).length" class="mark-slot" @click.stop>
                <template v-if="marksOf(chapter.id).length === 1">
                  <button class="mark-quote" type="button" @click="onMarkClick(chapter)">{{ shortQuote(marksOf(chapter.id)[0].quote) }}</button>
                  <button class="mark-delete" type="button" @click="removeMark(marksOf(chapter.id)[0].id)">删除</button>
                </template>
                <template v-else>
                  <template v-if="markMenu !== chapter.id">
                    <button class="mark-quote" type="button" @click="onMarkClick(chapter)">{{ shortQuote(marksOf(chapter.id)[0].quote) }}</button>
                    <button class="mark-delete" type="button" @click="removeMark(marksOf(chapter.id)[0].id)">删除</button>
                  </template>
                  <div v-if="markMenu === chapter.id" class="mark-menu">
                    <div v-for="mark in marksOf(chapter.id)" :key="mark.id" class="mark-entry">
                      <button class="mark-quote" type="button" @click="jumpToMark(chapter, mark)">{{ shortQuote(mark.quote) }}</button>
                      <button class="mark-delete" type="button" @click="removeMark(mark.id)">删除</button>
                    </div>
                  </div>
                </template>
              </div>
            </div>
          </template>
        </div>
        <div
          v-else
          class="chapter-item"
          :class="{ active: block.chapter.id === activeId }"
          draggable="true"
          @dragstart="onChapterDrag(block.chapter.id, $event)"
          @dragover.prevent
          @drop="onChapterDrop(block.chapter.id, $event)"
          @click="openChapter(block.chapter.id)"
        >
          <strong>{{ block.chapter.title }}</strong>
          <div class="meta"><span>{{ block.chapter.word_count }} 字</span><span v-if="worldNameOf(block.chapter.world_id || '')">{{ worldNameOf(block.chapter.world_id || '') }}</span></div>
          <div v-if="marksOf(block.chapter.id).length" class="mark-slot" @click.stop>
            <template v-if="marksOf(block.chapter.id).length === 1">
              <button class="mark-quote" type="button" @click="onMarkClick(block.chapter)">{{ shortQuote(marksOf(block.chapter.id)[0].quote) }}</button>
              <button class="mark-delete" type="button" @click="removeMark(marksOf(block.chapter.id)[0].id)">删除</button>
            </template>
            <template v-else>
              <template v-if="markMenu !== block.chapter.id">
                <button class="mark-quote" type="button" @click="onMarkClick(block.chapter)">{{ shortQuote(marksOf(block.chapter.id)[0].quote) }}</button>
                <button class="mark-delete" type="button" @click="removeMark(marksOf(block.chapter.id)[0].id)">删除</button>
              </template>
              <div v-if="markMenu === block.chapter.id" class="mark-menu">
                <div v-for="mark in marksOf(block.chapter.id)" :key="mark.id" class="mark-entry">
                  <button class="mark-quote" type="button" @click="jumpToMark(block.chapter, mark)">{{ shortQuote(mark.quote) }}</button>
                  <button class="mark-delete" type="button" @click="removeMark(mark.id)">删除</button>
                </div>
              </div>
            </template>
          </div>
        </div>
      </template>
    </aside>
    <section class="manuscript" @click="toolMenu = false; worldPick = false">
      <div class="manuscript-tools">
        <div>
          <input v-if="activeChapter" v-model="activeChapter.title" class="editor-title chapter-name" aria-label="章节名" @blur="rename(activeChapter)" />
          <div class="meta">
            <span class="world-pick">
              <button class="text-button" type="button" @click.stop="worldPick = !worldPick">{{ chapterWorldName || "选择世界" }}</button>
              <div v-if="worldPick" class="menu-list" @click.stop>
                <button v-for="world in allWorlds" :key="world.id" type="button" @click="chooseChapterWorld(world.id)">{{ world.name }}</button>
                <p v-if="allWorlds.length === 0" class="muted">还没有世界</p>
              </div>
            </span>
            <span>{{ saveState }}</span>
          </div>
        </div>
        <div class="actions">
          <button class="history-icon" type="button" aria-label="撤销" @click="editor?.chain().focus().undo().run()">
            <svg viewBox="0 0 24 24" width="18" height="18" aria-hidden="true"><path d="M9 14 4 9l5-5" /><path d="M4 9h10.5a5.5 5.5 0 0 1 5.5 5.5a5.5 5.5 0 0 1-5.5 5.5H11" /></svg>
          </button>
          <button class="history-icon" type="button" aria-label="重做" @click="editor?.chain().focus().redo().run()">
            <svg viewBox="0 0 24 24" width="18" height="18" aria-hidden="true"><path d="m15 14 5-5-5-5" /><path d="M20 9H9.5A5.5 5.5 0 0 0 4 14.5a5.5 5.5 0 0 0 5.5 5.5H13" /></svg>
          </button>
          <button class="text-button" type="button" @click="chaptersOpen = !chaptersOpen">{{ chaptersOpen ? "收起目录" : "展开目录" }}</button>
          <button class="text-button" type="button" @click="assistOpen = !assistOpen">{{ assistOpen ? "收起建议" : "展开建议" }}</button>
          <span class="tool-menu">
            <button class="icon-button" type="button" aria-label="更多功能" @click.stop="toolMenu = !toolMenu">⋯</button>
            <div v-if="toolMenu" class="menu-list" @click.stop>
              <button type="button" @click="persist">{{ saveState === "保存失败" ? "重试" : "保存" }}</button>
              <button type="button" @click="toolsOpen = !toolsOpen">查找</button>
              <button type="button" @click="toggleRevisions">版本</button>
              <a :href="`/api/novels/${novel.id}/export.txt`">TXT</a>
              <a :href="`/api/novels/${novel.id}/export.docx`">DOCX</a>
              <a :href="`/api/novels/${novel.id}/export.pdf`">PDF</a>
              <button v-if="chapters.length > 1 && activeChapter" class="danger" type="button" @click="removeChapter(activeChapter)">删除章节</button>
            </div>
          </span>
        </div>
      </div>
      <div class="paper">
        <div v-show="toolsOpen" class="actions tools-row">
          <NInput v-model:value="findText" size="small" placeholder="查找" />
          <NInput v-model:value="replaceText" size="small" placeholder="替换" />
          <NButton size="small" @click="replaceTextInChapter(false)">替换</NButton>
          <NButton size="small" @click="replaceTextInChapter(true)">全部替换</NButton>
        </div>
        <BubbleMenu v-if="editor" :editor="editor" :tippy-options="{ duration: 120, placement: 'top' }" :should-show="({ editor: current }) => !current.state.selection.empty">
          <div class="selection-menu">
            <button type="button" @mousedown.prevent @click="markSelection">标记</button>
            <button type="button" @mousedown.prevent @click="createCharacterFromSelection">新建角色</button>
            <button type="button" @mousedown.prevent @click="createForeshadowFromSelection">新建伏笔</button>
            <button type="button" @mousedown.prevent @click="cutSelection">剪切</button>
            <button type="button" @mousedown.prevent @click="copySelection">复制</button>
            <button type="button" @mousedown.prevent @click="selectAllText">全选</button>
          </div>
        </BubbleMenu>
        <EditorContent :editor="editor" />
        <div v-if="showRevisions" style="margin-top: 18px">
          <p v-if="revisions.length === 0" class="muted">还没有更早的版本。正文变化后会自动留下一份。</p>
          <div v-for="revision in revisions" :key="revision.id" class="section-title">
            <span class="muted">{{ new Date(revision.created_at).toLocaleString() }} · {{ revision.word_count }} 字</span>
            <NButton size="tiny" @click="restore(revision)">恢复</NButton>
          </div>
        </div>
      </div>
    </section>
    <aside v-show="assistOpen" class="assist">
      <strong>写作建议</strong>
      <p class="muted">选中文字后可以扩写、润色或改写。续写可以不选中，从章末接着写。建议确认后才会进入正文。</p>
      <div class="actions" style="margin: 12px 0; flex-wrap: wrap">
        <NButton v-for="action in actions" :key="action.key" size="small" :loading="asking" @click="ask(action.key)">{{ action.label }}</NButton>
        <NButton v-for="action in analysis" :key="action.key" size="small" quaternary :loading="asking" @click="ask(action.key)">{{ action.label }}</NButton>
      </div>
      <article v-if="suggestion" class="card" style="padding: 14px">
        <div class="meta">
          <span>{{ actions.find((item) => item.key === suggestion?.action)?.label }}</span>
          <span>{{ suggestion.provider === "demo" ? "本地示例" : "模型" }}</span>
        </div>
        <p v-if="suggestion.source_text" class="suggestion removed">{{ suggestion.source_text }}</p>
        <p class="suggestion">{{ suggestion.suggestion }}</p>
        <div class="actions">
          <NButton size="small" type="primary" @click="accept">确认写入</NButton>
          <NButton size="small" @click="reject">放弃</NButton>
        </div>
      </article>
    </aside>
  </div>
  <NModal v-model:show="volumeNameOpen" preset="card" title="新建分卷" style="width: 420px">
    <NInput v-model:value="volumeName" placeholder="分卷名称" @keyup.enter="confirmVolumeName(false)" />
    <div class="actions" style="margin-top: 16px">
      <NButton @click="confirmVolumeName(true)">使用默认名（{{ defaultVolumeTitle() }}）</NButton>
      <NButton type="primary" :disabled="!volumeName.trim()" @click="confirmVolumeName(false)">确定</NButton>
    </div>
  </NModal>
  <NModal v-model:show="volumePickOpen" preset="card" title="选择章节" style="width: 420px">
    <div class="volume-choices">
      <label v-for="chapter in chapters" :key="chapter.id">
        <input type="checkbox" :checked="volumePickIds.includes(chapter.id)" @change="toggleVolumePick(chapter.id)" />
        <span>{{ chapter.title }}</span>
      </label>
    </div>
    <p class="muted">选中首尾章节后，中间的章节会一并加入。</p>
    <div class="actions">
      <NButton @click="volumePickOpen = false">取消</NButton>
      <NButton type="primary" @click="confirmVolumePick">确定</NButton>
    </div>
  </NModal>
</template>
