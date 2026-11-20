<script setup lang="ts">
import { NButton, NForm, NFormItem, NInput, NInputNumber, NModal, NSelect, useDialog, useMessage } from "naive-ui"
import { computed, onMounted, reactive, ref } from "vue"
import { useRouter } from "vue-router"
import { api } from "../api"
import type { Novel, World } from "../types"

const router = useRouter()
const message = useMessage()
const dialog = useDialog()
const novels = ref<Novel[]>([])
const worlds = ref<World[]>([])
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
  world_id: null as string | null,
})
const worldForm = reactive({ name: "", summary: "", id: "" })

const statusOptions = [
  { label: "构思中", value: "draft" },
  { label: "创作中", value: "writing" },
  { label: "已完结", value: "finished" },
]
const worldOptions = computed(() => worlds.value.map((world) => ({ label: world.name, value: world.id })))
const totalWords = computed(() => novels.value.reduce((sum, novel) => sum + novel.word_count, 0))

function statusLabel(status: Novel["status"]) {
  return statusOptions.find((item) => item.value === status)?.label ?? status
}

async function reload() {
  loading.value = true
  try {
    ;[novels.value, worlds.value] = await Promise.all([api.novels(), api.worlds()])
  } catch (error) {
    message.error(error instanceof Error ? error.message : "加载失败")
  } finally {
    loading.value = false
  }
}

function openCreateNovel() {
  editingId.value = null
  Object.assign(novelForm, { title: "", summary: "", genre: "", status: "draft", target_words: 0, world_id: null })
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
    world_id: novel.worlds[0]?.id ?? null,
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
        world_id: novelForm.world_id,
        clear_world: novelForm.world_id === null,
      })
    } else {
      const created = await api.createNovel({ ...novelForm })
      novelOpen.value = false
      await router.push(`/novels/${created.id}`)
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
</script>

<template>
  <main class="page">
    <div class="page-head">
      <div>
        <h1>工作台</h1>
        <p class="muted">先放下一本小说，再把它放进一个世界。</p>
      </div>
    </div>
    <section class="stats">
      <div class="stat"><span class="muted">小说</span><b>{{ novels.length }}</b></div>
      <div class="stat"><span class="muted">世界</span><b>{{ worlds.length }}</b></div>
      <div class="stat"><span class="muted">已写字数</span><b>{{ totalWords }}</b></div>
    </section>
    <div class="grid">
      <section>
        <div class="section-title">
          <h2>我的小说</h2>
          <NButton type="primary" @click="openCreateNovel">创建小说</NButton>
        </div>
        <div v-if="!loading && novels.length === 0" class="empty">还没有小说。</div>
        <div class="card-list">
          <article v-for="novel in novels" :key="novel.id" class="card novel-card">
            <div>
              <h2>{{ novel.title }}</h2>
              <p class="muted">{{ novel.summary || "还没有简介" }}</p>
              <div class="meta">
                <span>{{ statusLabel(novel.status) }}</span>
                <span>{{ novel.word_count }} 字</span>
                <span>{{ novel.chapter_count }} 章</span>
                <span>{{ novel.worlds[0]?.name || "未关联世界" }}</span>
              </div>
            </div>
            <div class="actions">
              <NButton size="small" type="primary" @click="router.push(`/novels/${novel.id}`)">写作</NButton>
              <NButton size="small" @click="openEditNovel(novel)">编辑</NButton>
              <NButton size="small" quaternary @click="removeNovel(novel)">删除</NButton>
            </div>
          </article>
        </div>
      </section>
      <section>
        <div class="section-title">
          <h2>我的世界</h2>
          <NButton @click="openCreateWorld">创建世界</NButton>
        </div>
        <div v-if="!loading && worlds.length === 0" class="empty">还没有世界。世界可以同时被多本小说引用。</div>
        <div class="card-list">
          <article v-for="world in worlds" :key="world.id" class="card world-card">
            <div>
              <h2>{{ world.name }}</h2>
              <p class="muted">{{ world.summary || "还没有介绍" }}</p>
              <div class="meta"><span>{{ world.novel_count }} 本小说</span></div>
            </div>
            <div class="actions">
              <NButton size="small" @click="openEditWorld(world)">编辑</NButton>
              <NButton size="small" quaternary @click="removeWorld(world)">删除</NButton>
            </div>
          </article>
        </div>
      </section>
    </div>

    <NModal v-model:show="novelOpen" preset="card" :title="editingId ? '编辑小说' : '创建小说'" style="width: 520px">
      <NForm label-placement="top">
        <NFormItem label="名称"><NInput v-model:value="novelForm.title" /></NFormItem>
        <NFormItem label="简介"><NInput v-model:value="novelForm.summary" type="textarea" :autosize="{ minRows: 3, maxRows: 6 }" /></NFormItem>
        <NFormItem label="类型"><NInput v-model:value="novelForm.genre" /></NFormItem>
        <NFormItem label="状态"><NSelect v-model:value="novelForm.status" :options="statusOptions" /></NFormItem>
        <NFormItem label="目标字数"><NInputNumber v-model:value="novelForm.target_words" :min="0" style="width: 100%" /></NFormItem>
        <NFormItem label="关联世界"><NSelect v-model:value="novelForm.world_id" clearable :options="worldOptions" placeholder="可以稍后关联" /></NFormItem>
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
