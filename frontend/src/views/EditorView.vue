<script setup lang="ts">
import { EditorContent, useEditor } from "@tiptap/vue-3"
import StarterKit from "@tiptap/starter-kit"
import { NButton, NInput, useDialog, useMessage } from "naive-ui"
import { computed, onBeforeUnmount, ref, watch } from "vue"
import { useRoute, useRouter } from "vue-router"
import { api } from "../api"
import type { AiAction, ChapterBrief, NovelDetail, Revision, Suggestion } from "../types"

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
const range = ref<{ from: number; to: number } | null>(null)
let savedHtml = ""
let hydrating = false
let timer = 0

const actions: { key: AiAction; label: string }[] = [
  { key: "continue", label: "续写" },
  { key: "expand", label: "扩写" },
  { key: "polish", label: "润色" },
  { key: "rewrite", label: "改写" },
]

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
  const detail = await api.novel(String(route.params.id))
  novel.value = detail
  chapters.value = detail.chapters
  const next = chapters.value.find((item) => item.id === activeId.value)?.id ?? chapters.value[0]?.id
  if (next) await openChapter(next)
}

async function openChapter(id: string) {
  if (activeId.value && activeId.value !== id) await persist()
  const chapter = await api.chapter(id)
  activeId.value = chapter.id
  hydrating = true
  editor.value?.commands.setContent(chapter.content || "<p></p>", false)
  hydrating = false
  savedHtml = editor.value?.getHTML() ?? chapter.content
  saveState.value = "已保存"
  suggestion.value = null
  showRevisions.value = false
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
    updated_at: created.updated_at,
  })
  await openChapter(created.id)
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

watch(() => route.params.id, () => void loadNovel().catch((error: unknown) => {
  message.error(error instanceof Error ? error.message : "小说不存在")
  void router.push("/")
}), { immediate: true })

onBeforeUnmount(() => {
  window.clearTimeout(timer)
  void persist()
  editor.value?.destroy()
})
</script>

<template>
  <div class="editor-shell" v-if="novel">
    <aside class="side">
      <div class="section-title">
        <strong>章节</strong>
        <NButton size="tiny" @click="addChapter">新增</NButton>
      </div>
      <div
        v-for="chapter in chapters"
        :key="chapter.id"
        class="chapter-item"
        :class="{ active: chapter.id === activeId }"
        @click="openChapter(chapter.id)"
      >
        <NInput v-model:value="chapter.title" size="small" @click.stop @blur="rename(chapter)" />
        <div class="meta"><span>{{ chapter.word_count }} 字</span></div>
      </div>
      <NButton v-if="chapters.length > 1" quaternary size="small" style="margin-top: 8px" @click="removeChapter(chapters.find((item) => item.id === activeId)!)">删除当前章</NButton>
    </aside>
    <section class="manuscript">
      <div class="paper">
        <div class="section-title">
          <div>
            <h1 class="editor-title">{{ novel.title }}</h1>
            <div class="meta"><span>{{ worldName }}</span><span>{{ saveState }}</span></div>
          </div>
          <NButton size="small" @click="toggleRevisions">版本</NButton>
        </div>
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
    <aside class="assist">
      <strong>写作建议</strong>
      <p class="muted">选中文字后可以扩写、润色或改写。续写可以不选中，从章末接着写。建议确认后才会进入正文。</p>
      <div class="actions" style="margin: 12px 0; flex-wrap: wrap">
        <NButton v-for="action in actions" :key="action.key" size="small" :loading="asking" @click="ask(action.key)">{{ action.label }}</NButton>
      </div>
      <article v-if="suggestion" class="card" style="padding: 14px">
        <div class="meta">
          <span>{{ actions.find((item) => item.key === suggestion?.action)?.label }}</span>
          <span>{{ suggestion.provider === "demo" ? "本地示例" : "模型" }}</span>
        </div>
        <p class="suggestion">{{ suggestion.suggestion }}</p>
        <div class="actions">
          <NButton size="small" type="primary" @click="accept">确认写入</NButton>
          <NButton size="small" @click="reject">放弃</NButton>
        </div>
      </article>
    </aside>
  </div>
</template>
