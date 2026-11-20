<script setup lang="ts">
import { BubbleMenu, EditorContent, useEditor } from "@tiptap/vue-3"
import StarterKit from "@tiptap/starter-kit"
import { NButton, NInput, useDialog, useMessage } from "naive-ui"
import { computed, onBeforeUnmount, ref, watch } from "vue"
import { RouterLink, useRoute, useRouter } from "vue-router"
import { api } from "../api"
import type { AiAction, ChapterBrief, NovelDetail, Revision, Suggestion, Volume } from "../types"

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
const volumes = ref<Volume[]>([])
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
  extensions: [StarterKit],
  onUpdate: () => {
    if (hydrating) return
    saveState.value = "未保存"
    window.clearTimeout(timer)
    timer = window.setTimeout(() => void persist(), 700)
  },
})

const worldName = computed(() => novel.value?.worlds[0]?.name || "未关联世界")

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
    updated_at: created.updated_at,
  })
  await openChapter(created.id)
}

async function moveChapter(chapter: ChapterBrief, direction: "up" | "down") {
  const rows = await api.moveChapter(chapter.id, direction)
  chapters.value = rows.map((row) => ({
    id: row.id,
    title: row.title,
    position: row.position,
    word_count: row.word_count,
    volume_id: row.volume_id,
    updated_at: row.updated_at,
  }))
}

async function addVolume() {
  if (!novel.value) return
  volumes.value.push(await api.createVolume(novel.value.id, `第${volumes.value.length + 1}卷`))
}

async function setVolume(chapter: ChapterBrief, volumeId: string) {
  const updated = await api.updateChapter(chapter.id, volumeId ? { volume_id: volumeId } : { clear_volume: true })
  chapter.volume_id = updated.volume_id
}

function onVolumeChange(chapter: ChapterBrief, event: Event) {
  const value = (event.target as HTMLSelectElement).value
  void setVolume(chapter, value)
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
  await api.createMark(activeId.value, { quote: picked.text, start: picked.from, end: picked.to })
  marks.value = await api.marks(activeId.value)
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
    <aside class="side">
      <div class="section-title">
        <strong>章节</strong>
        <span class="actions">
          <button class="text-button" type="button" @click="addVolume">分卷</button>
          <button class="text-button" type="button" @click="addChapter">新增</button>
        </span>
      </div>
      <div
        v-for="chapter in chapters"
        :key="chapter.id"
        class="chapter-item"
        :class="{ active: chapter.id === activeId }"
        @click="openChapter(chapter.id)"
      >
        <NInput v-model:value="chapter.title" size="small" @click.stop @blur="rename(chapter)" />
        <select class="volume-select" :value="chapter.volume_id || ''" @click.stop @change="onVolumeChange(chapter, $event)">
          <option value="">未分卷</option>
          <option v-for="volume in volumes" :key="volume.id" :value="volume.id">{{ volume.title }}</option>
        </select>
        <div class="meta">
          <span>{{ chapter.word_count }} 字</span>
          <button type="button" class="text-button" @click.stop="moveChapter(chapter, 'up')">上移</button>
          <button type="button" class="text-button" @click.stop="moveChapter(chapter, 'down')">下移</button>
        </div>
      </div>
      <button v-if="chapters.length > 1" class="text-button" type="button" @click="removeChapter(chapters.find((item) => item.id === activeId)!)">删除当前章</button>
      <div class="section-title" style="margin-top: 18px"><strong>标记</strong></div>
      <button v-for="mark in marks" :key="mark.id" class="chapter-item" type="button" @click="revealMark(mark)">
        <span class="summary">{{ mark.quote }}</span>
        <span class="text-button" @click.stop="removeMark(mark.id)">删除</span>
      </button>
      <p v-if="marks.length === 0" class="muted">选中正文后可以标记，方便以后回到这里。</p>
    </aside>
    <section class="manuscript">
      <div class="paper">
        <div class="section-title">
          <div>
            <h1 class="editor-title">{{ novel.title }}</h1>
            <div class="meta"><span>{{ worldName }}</span><span>{{ saveState }}</span></div>
          </div>
          <div class="actions">
            <button class="text-button" type="button" @click="editor?.chain().focus().undo().run()">撤销</button>
            <button class="text-button" type="button" @click="editor?.chain().focus().redo().run()">重做</button>
            <NButton size="small" type="primary" @click="persist">{{ saveState === "保存失败" ? "重试" : "保存" }}</NButton>
            <button class="text-button" type="button" @click="toolsOpen = !toolsOpen">查找</button>
            <button class="text-button" type="button" @click="toggleRevisions">版本</button>
            <button class="text-button" type="button" @click="chaptersOpen = !chaptersOpen">{{ chaptersOpen ? "收起目录" : "目录" }}</button>
            <button class="text-button" type="button" @click="assistOpen = !assistOpen">{{ assistOpen ? "收起建议" : "建议" }}</button>
          </div>
        </div>
        <div class="meta export-links">
          <a :href="`/api/novels/${novel.id}/export.txt`">TXT</a>
          <a :href="`/api/novels/${novel.id}/export.docx`">DOCX</a>
          <a :href="`/api/novels/${novel.id}/export.pdf`">PDF</a>
        </div>
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
</template>
