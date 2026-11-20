<script setup lang="ts">
import { NButton, NForm, NFormItem, NInput, NInputNumber, NModal, NSelect, useDialog, useMessage } from "naive-ui"
import { computed, onMounted, reactive, ref, watch } from "vue"
import { useRoute, useRouter } from "vue-router"
import { api } from "../api"
import { libraryTick } from "../library"
import type { Character, Foreshadow, Novel, PendingSuggestion, World } from "../types"

const route = useRoute()
const router = useRouter()
const showingWorlds = computed(() => route.path === "/worlds")
const message = useMessage()
const dialog = useDialog()
const novels = ref<Novel[]>([])
const worlds = ref<World[]>([])
const inbox = ref<Foreshadow[]>([])
const pending = ref<PendingSuggestion[]>([])
const characters = ref<Character[]>([])
const showArchived = ref(false)
const fileInput = ref<HTMLInputElement | null>(null)
const loading = ref(true)
const novelOpen = ref(false)
const worldOpen = ref(false)
const editingId = ref<string | null>(null)

const novelForm = reactive({
  title: "",
  summary: "",
  genre: "",
  status: "draft" as Novel["status"],
  target_words: 0,
  tags: "",
  cover_url: "",
  world_ids: [] as string[],
  character_ids: [] as string[],
})
const worldForm = reactive({ name: "", summary: "", id: "" })

const statusOptions = [
  { label: "构思中", value: "draft" },
  { label: "创作中", value: "writing" },
  { label: "已完结", value: "finished" },
]
const worldOptions = computed(() => worlds.value.map((world) => ({ label: world.name, value: world.id })))
const characterOptions = computed(() => characters.value.map((row) => ({ label: row.name, value: row.id })))
const totalWords = computed(() => novels.value.reduce((sum, novel) => sum + novel.word_count, 0))
const totalChapters = computed(() => novels.value.reduce((sum, novel) => sum + novel.chapter_count, 0))
const recentNovels = computed(() => novels.value.slice(0, 5))
const recentWorlds = computed(() => [...worlds.value].sort((a, b) => b.updated_at.localeCompare(a.updated_at)).slice(0, 5))

function statusLabel(status: Novel["status"]) {
  return statusOptions.find((item) => item.value === status)?.label ?? status
}

async function reload() {
  loading.value = true
  try {
    ;[novels.value, worlds.value, inbox.value, pending.value, characters.value] = await Promise.all([
      api.novels(showArchived.value),
      api.worlds(),
      api.foreshadowInbox(),
      api.pendingSuggestions(),
      api.characters(),
    ])
  } catch (error) {
    message.error(error instanceof Error ? error.message : "加载失败")
  } finally {
    loading.value = false
  }
}

function openCreateNovel() {
  editingId.value = null
  Object.assign(novelForm, { title: "", summary: "", genre: "", status: "draft", target_words: 0, tags: "", cover_url: "", world_ids: [], character_ids: [] })
  novelOpen.value = true
}

function openEditNovel(novel: Novel) {
  editingId.value = novel.id
  Object.assign(novelForm, {
    title: novel.title,
    summary: novel.summary,
    genre: novel.genre,
    status: novel.status,
    target_words: novel.target_words,
    tags: novel.tags,
    cover_url: novel.cover_url,
    world_ids: novel.worlds.map((row) => row.id),
    character_ids: novel.characters.map((row) => row.id),
  })
  novelOpen.value = true
}

async function saveNovel() {
  if (!novelForm.title.trim()) {
    message.warning("请填写小说名称")
    return
  }
  try {
    if (editingId.value) {
      await api.updateNovel(editingId.value, {
        title: novelForm.title,
        summary: novelForm.summary,
        genre: novelForm.genre,
        status: novelForm.status,
        target_words: novelForm.target_words,
        tags: novelForm.tags,
        cover_url: novelForm.cover_url,
        world_ids: novelForm.world_ids,
        character_ids: novelForm.character_ids,
      })
    } else {
      const created = await api.createNovel({ ...novelForm })
      novelOpen.value = false
      await router.push(`/novels/${created.id}/overview`)
      return
    }
    novelOpen.value = false
    await reload()
  } catch (error) {
    message.error(error instanceof Error ? error.message : "保存失败")
  }
}

function openCreateWorld() {
  Object.assign(worldForm, { name: "", summary: "", id: "" })
  worldOpen.value = true
}

function openEditWorld(world: World) {
  Object.assign(worldForm, { name: world.name, summary: world.summary, id: world.id })
  worldOpen.value = true
}

async function saveWorld() {
  if (!worldForm.name.trim()) {
    message.warning("请填写世界名称")
    return
  }
  try {
    if (worldForm.id) await api.updateWorld(worldForm.id, { name: worldForm.name, summary: worldForm.summary })
    else await api.createWorld({ name: worldForm.name, summary: worldForm.summary })
    worldOpen.value = false
    await reload()
  } catch (error) {
    message.error(error instanceof Error ? error.message : "保存失败")
  }
}

function removeNovel(novel: Novel) {
  dialog.warning({
    title: "删除小说",
    content: `删除《${novel.title}》后，章节会一起删除。关联的世界会保留。`,
    positiveText: "删除",
    negativeText: "取消",
    onPositiveClick: async () => {
      try {
        await api.deleteNovel(novel.id)
        await reload()
      } catch (error) {
        message.error(error instanceof Error ? error.message : "删除失败")
      }
    },
  })
}

async function duplicate(novel: Novel) {
  const created = await api.duplicateNovel(novel.id)
  message.success("已复制小说")
  await router.push(`/novels/${created.id}/overview`)
}

async function archive(novel: Novel) {
  await api.updateNovel(novel.id, { archived: !novel.archived })
  await reload()
}

async function importNovel(event: Event) {
  const input = event.target as HTMLInputElement
  const file = input.files?.[0]
  input.value = ""
  if (!file) return
  try {
    const body = JSON.parse(await file.text()) as Record<string, unknown>
    const created = await api.importNovel(body)
    message.success("已导入基础数据")
    await router.push(`/novels/${created.id}/overview`)
  } catch (error) {
    message.error(error instanceof Error ? error.message : "导入失败")
  }
}

function removeWorld(world: World) {
  dialog.warning({
    title: "删除世界",
    content: `删除「${world.name}」。如果还有小说关联它，删除会被拒绝。`,
    positiveText: "删除",
    negativeText: "取消",
    onPositiveClick: async () => {
      try {
        await api.deleteWorld(world.id)
        await reload()
      } catch (error) {
        message.error(error instanceof Error ? error.message : "删除失败")
      }
    },
  })
}

onMounted(reload)
watch(libraryTick, () => void reload())
watch(showArchived, () => void reload())
</script>

<template>
  <main class="page">
    <header class="workspace-head">
      <div>
        <h1>{{ showingWorlds ? "世界" : "小说" }}</h1>
        <p class="muted">
          <template v-if="showingWorlds">{{ worlds.length }} 个世界，可被多本小说引用</template>
          <template v-else>{{ novels.length }} 本 · {{ totalChapters }} 章 · {{ totalWords }} 字</template>
        </p>
      </div>
      <div class="actions">
        <template v-if="!showingWorlds">
          <NButton size="small" @click="showArchived = !showArchived">{{ showArchived ? "隐藏归档" : "显示归档" }}</NButton>
          <NButton size="small" @click="fileInput?.click()">导入 JSON</NButton>
          <input ref="fileInput" type="file" accept="application/json,.json" hidden @change="importNovel" />
          <NButton size="small" type="primary" @click="openCreateNovel">创建小说</NButton>
        </template>
        <NButton v-else size="small" type="primary" @click="openCreateWorld">创建世界</NButton>
      </div>
    </header>

    <section v-if="!showingWorlds">
      <div v-if="!loading && novels.length === 0" class="empty">还没有小说。</div>
      <div v-else class="card-grid">
        <article v-for="novel in novels" :key="novel.id" class="card library-card">
          <div>
            <h2>{{ novel.title }}</h2>
            <p class="muted summary">{{ novel.summary || "还没有简介" }}</p>
          </div>
          <div class="meta">
            <span>{{ statusLabel(novel.status) }}</span>
            <span>{{ novel.word_count }} 字</span>
            <span>{{ novel.chapter_count }} 章</span>
            <span>{{ novel.worlds.map((row) => row.name).join("、") || "未关联世界" }}</span>
            <span>{{ novel.characters.map((row) => row.name).join("、") || "未关联角色" }}</span>
            <span v-if="novel.archived">已归档</span>
          </div>
          <div class="actions">
            <NButton size="small" type="primary" @click="router.push(`/novels/${novel.id}/overview`)">进入</NButton>
            <button class="text-button" type="button" @click="openEditNovel(novel)">编辑</button>
            <button class="text-button" type="button" @click="duplicate(novel)">复制</button>
            <button class="text-button" type="button" @click="archive(novel)">{{ novel.archived ? "取消归档" : "归档" }}</button>
            <a class="text-button" :href="`/api/novels/${novel.id}/export.txt`">导出</a>
            <button class="text-button danger" type="button" @click="removeNovel(novel)">删除</button>
          </div>
        </article>
      </div>
    </section>

    <section v-else>
      <div v-if="!loading && worlds.length === 0" class="empty">还没有世界。</div>
      <div v-else class="card-grid">
        <article v-for="world in worlds" :key="world.id" class="card library-card">
          <div>
            <h2>{{ world.name }}</h2>
            <p class="muted summary">{{ world.summary || "还没有介绍" }}</p>
          </div>
          <div class="meta"><span>{{ world.novel_count }} 本小说</span></div>
          <div class="actions">
            <NButton size="small" type="primary" @click="router.push(`/worlds/${world.id}/overview`)">查看</NButton>
            <button class="text-button" type="button" @click="openEditWorld(world)">编辑</button>
            <button class="text-button danger" type="button" @click="removeWorld(world)">删除</button>
          </div>
        </article>
      </div>
    </section>

    <NModal v-model:show="novelOpen" preset="card" :title="editingId ? '编辑小说' : '创建小说'" style="width: 520px">
      <NForm label-placement="top">
        <NFormItem label="名称"><NInput v-model:value="novelForm.title" /></NFormItem>
        <NFormItem label="简介"><NInput v-model:value="novelForm.summary" type="textarea" :autosize="{ minRows: 3, maxRows: 6 }" /></NFormItem>
        <NFormItem label="类型"><NInput v-model:value="novelForm.genre" /></NFormItem>
        <NFormItem label="状态"><NSelect v-model:value="novelForm.status" :options="statusOptions" /></NFormItem>
        <NFormItem label="目标字数"><NInputNumber v-model:value="novelForm.target_words" :min="0" style="width: 100%" /></NFormItem>
        <NFormItem label="标签"><NInput v-model:value="novelForm.tags" placeholder="用逗号分开" /></NFormItem>
        <NFormItem label="封面地址"><NInput v-model:value="novelForm.cover_url" placeholder="图片地址，素材库以后再做" /></NFormItem>
        <NFormItem label="关联世界"><NSelect v-model:value="novelForm.world_ids" multiple :options="worldOptions" placeholder="可以稍后关联" /></NFormItem>
        <NFormItem label="关联角色"><NSelect v-model:value="novelForm.character_ids" multiple :options="characterOptions" placeholder="可以稍后关联" /></NFormItem>
      </NForm>
      <template #footer>
        <NButton type="primary" @click="saveNovel">保存</NButton>
      </template>
    </NModal>

    <NModal v-model:show="worldOpen" preset="card" :title="worldForm.id ? '编辑世界' : '创建世界'" style="width: 480px">
      <NForm label-placement="top">
        <NFormItem label="名称"><NInput v-model:value="worldForm.name" /></NFormItem>
        <NFormItem label="介绍"><NInput v-model:value="worldForm.summary" type="textarea" :autosize="{ minRows: 3, maxRows: 6 }" /></NFormItem>
      </NForm>
      <template #footer>
        <NButton type="primary" @click="saveWorld">保存</NButton>
      </template>
    </NModal>
  </main>
</template>
