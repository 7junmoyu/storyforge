<script setup lang="ts">
import { NButton, NForm, NFormItem, NInput, NModal, useDialog, useMessage } from "naive-ui"
import { computed, onMounted, reactive, ref, watch } from "vue"
import { useRoute, useRouter } from "vue-router"
import { api } from "../api"
import CoverField from "../components/CoverField.vue"
import { coverSrc, novelCovers, worldCovers } from "../covers"
import { libraryTick } from "../library"
import type { Character, Foreshadow, Novel, NovelGroup, PendingSuggestion, World } from "../types"

const route = useRoute()
const router = useRouter()
const showingWorlds = computed(() => route.path === "/worlds")
const message = useMessage()
const dialog = useDialog()
const novels = ref<Novel[]>([])
const groups = ref<NovelGroup[]>([])
const worlds = ref<World[]>([])
const inbox = ref<Foreshadow[]>([])
const pending = ref<PendingSuggestion[]>([])
const characters = ref<Character[]>([])
const fileInput = ref<HTMLInputElement | null>(null)
const loading = ref(true)
const novelOpen = ref(false)
const worldOpen = ref(false)
const groupOpen = ref(false)
const editingId = ref<string | null>(null)
const openGroupId = ref<string | null>(null)
const menuKey = ref("")
const dropGroupId = ref("")
const ignoreClick = ref(false)
const groupName = ref("")
const editingGroupId = ref("")

const novelForm = reactive({
  title: "",
  summary: "",
  cover_url: "",
  world_ids: [] as string[],
  character_ids: [] as string[],
})
const worldForm = reactive({ name: "", summary: "", cover_url: "", id: "" })

const totalWords = computed(() => novels.value.reduce((sum, novel) => sum + novel.word_count, 0))
const totalChapters = computed(() => novels.value.reduce((sum, novel) => sum + novel.chapter_count, 0))
const openGroup = computed(() => groups.value.find((group) => group.id === openGroupId.value) || null)
const shelfNovels = computed(() => novels.value.filter((novel) => (openGroupId.value ? novel.group_id === openGroupId.value : !novel.group_id)))

function groupCovers(groupId: string) {
  return novels.value
    .filter((novel) => novel.group_id === groupId)
    .sort((a, b) => (b.grouped_at || "").localeCompare(a.grouped_at || ""))
    .slice(0, 4)
}

async function reload() {
  loading.value = true
  try {
    ;[novels.value, groups.value, worlds.value, inbox.value, pending.value, characters.value] = await Promise.all([
      api.novels(true),
      api.novelGroups(),
      api.worlds(),
      api.foreshadowInbox(),
      api.pendingSuggestions(),
      api.characters(),
    ])
    if (openGroupId.value && !groups.value.some((group) => group.id === openGroupId.value)) openGroupId.value = null
  } catch (error) {
    message.error(error instanceof Error ? error.message : "加载失败")
  } finally {
    loading.value = false
  }
}

function openCreateNovel() {
  editingId.value = null
  Object.assign(novelForm, { title: "", summary: "", cover_url: novelCovers[0].url, world_ids: [], character_ids: [] })
  novelOpen.value = true
}

function openEditNovel(novel: Novel) {
  menuKey.value = ""
  editingId.value = novel.id
  Object.assign(novelForm, {
    title: novel.title,
    summary: novel.summary,
    cover_url: novel.cover_url || novelCovers[0].url,
    world_ids: novel.worlds.map((row) => row.id),
    character_ids: novel.characters.map((row) => row.id),
  })
  novelOpen.value = true
}

function toggleId(list: string[], id: string) {
  const index = list.indexOf(id)
  if (index >= 0) list.splice(index, 1)
  else list.push(id)
}

async function saveNovel() {
  if (!novelForm.title.trim()) {
    message.warning("请填写小说名称")
    return
  }
  try {
    const body = {
      title: novelForm.title,
      summary: novelForm.summary,
      cover_url: novelForm.cover_url,
      world_ids: novelForm.world_ids,
      character_ids: novelForm.character_ids,
    }
    if (editingId.value) await api.updateNovel(editingId.value, body)
    else {
      const created = await api.createNovel(body)
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
  Object.assign(worldForm, { name: "", summary: "", cover_url: worldCovers[0].url, id: "" })
  worldOpen.value = true
}

function openEditWorld(world: World) {
  Object.assign(worldForm, { name: world.name, summary: world.summary, cover_url: world.cover_url || worldCovers[0].url, id: world.id })
  worldOpen.value = true
}

async function saveWorld() {
  if (!worldForm.name.trim()) {
    message.warning("请填写世界名称")
    return
  }
  try {
    const body = { name: worldForm.name, summary: worldForm.summary, cover_url: worldForm.cover_url }
    if (worldForm.id) await api.updateWorld(worldForm.id, body)
    else await api.createWorld(body)
    worldOpen.value = false
    await reload()
  } catch (error) {
    message.error(error instanceof Error ? error.message : "保存失败")
  }
}

function removeNovel(novel: Novel) {
  menuKey.value = ""
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
  menuKey.value = ""
  const created = await api.duplicateNovel(novel.id)
  message.success("已复制小说")
  await router.push(`/novels/${created.id}/overview`)
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

function openGroupForm(group?: NovelGroup) {
  menuKey.value = ""
  editingGroupId.value = group?.id || ""
  groupName.value = group?.name || ""
  groupOpen.value = true
}

async function saveGroup() {
  if (!groupName.value.trim()) return
  if (editingGroupId.value) await api.renameNovelGroup(editingGroupId.value, groupName.value.trim())
  else await api.createNovelGroup(groupName.value.trim())
  groupOpen.value = false
  await reload()
}

function removeGroup(group: NovelGroup) {
  menuKey.value = ""
  dialog.warning({
    title: "删除分类",
    content: `删除「${group.name}」后，里面的小说会回到列表里，小说本身不会删除。`,
    positiveText: "删除",
    negativeText: "取消",
    onPositiveClick: async () => {
      await api.deleteNovelGroup(group.id)
      if (openGroupId.value === group.id) openGroupId.value = null
      await reload()
    },
  })
}

function dragNovel(novel: Novel, event: DragEvent) {
  ignoreClick.value = true
  event.dataTransfer?.setData("text/plain", novel.id)
  if (event.dataTransfer) event.dataTransfer.effectAllowed = "move"
}

async function dropOnGroup(group: NovelGroup, event: DragEvent) {
  dropGroupId.value = ""
  ignoreClick.value = true
  const novelId = event.dataTransfer?.getData("text/plain")
  if (!novelId) return
  await api.updateNovel(novelId, { group_id: group.id })
  await reload()
}

async function leaveGroup(novel: Novel) {
  menuKey.value = ""
  await api.updateNovel(novel.id, { group_id: null })
  await reload()
}

function enterNovel(id: string) {
  if (ignoreClick.value) {
    ignoreClick.value = false
    return
  }
  if (menuKey.value) {
    menuKey.value = ""
    return
  }
  void router.push(`/novels/${id}/overview`)
}

function openShelfGroup(id: string) {
  if (ignoreClick.value) {
    ignoreClick.value = false
    return
  }
  openGroupId.value = id
}

onMounted(reload)
watch(libraryTick, () => void reload())
</script>

<template>
  <main class="page" @click="menuKey = ''">
    <header class="workspace-head">
      <div>
        <h1>{{ showingWorlds ? "世界" : openGroup ? openGroup.name : "小说" }}</h1>
        <p class="muted">
          <template v-if="showingWorlds">{{ worlds.length }} 个世界，可被多本小说引用</template>
          <template v-else>{{ novels.length }} 本 · {{ totalChapters }} 章 · {{ totalWords }} 字</template>
        </p>
      </div>
      <div class="actions">
        <template v-if="!showingWorlds">
          <button v-if="openGroup" class="text-button" type="button" @click="openGroupId = null">返回全部</button>
          <NButton size="small" @click="fileInput?.click()">导入 JSON</NButton>
          <input ref="fileInput" type="file" accept="application/json,.json" hidden @change="importNovel" />
          <NButton size="small" @click="openGroupForm()">添加分类</NButton>
          <NButton size="small" type="primary" @click="openCreateNovel">创建小说</NButton>
        </template>
        <NButton v-else size="small" type="primary" @click="openCreateWorld">创建世界</NButton>
      </div>
    </header>

    <section v-if="!showingWorlds">
      <div v-if="!loading && novels.length === 0 && groups.length === 0" class="empty">还没有小说。</div>
      <div v-else class="book-shelf">
        <article
          v-for="group in openGroup ? [] : groups"
          :key="group.id"
          class="book-card"
          :class="{ 'drop-ready': dropGroupId === group.id }"
          @click="openShelfGroup(group.id)"
          @dragover.prevent="dropGroupId = group.id"
          @dragleave="dropGroupId = ''"
          @drop.prevent="dropOnGroup(group, $event)"
        >
          <div class="cover-mosaic">
            <img v-for="novel in groupCovers(group.id)" :key="novel.id" :src="coverSrc(novel.cover_url)" alt="" />
          </div>
          <div class="book-copy">
            <h2>{{ group.name }}</h2>
            <p class="muted">{{ novels.filter((novel) => novel.group_id === group.id).length }} 本小说</p>
          </div>
          <div class="card-menu" @click.stop>
            <button class="icon-button" type="button" aria-label="分类设置" @click="menuKey = menuKey === group.id ? '' : group.id">⋯</button>
            <div v-if="menuKey === group.id" class="menu-list">
              <button type="button" @click="openGroupForm(group)">改名</button>
              <button class="danger" type="button" @click="removeGroup(group)">删除分类</button>
            </div>
          </div>
        </article>

        <article
          v-for="novel in shelfNovels"
          :key="novel.id"
          class="book-card"
          draggable="true"
          @dragstart="dragNovel(novel, $event)"
          @click="enterNovel(novel.id)"
        >
          <img class="book-cover" :src="coverSrc(novel.cover_url)" alt="" />
          <div class="book-copy">
            <h2>{{ novel.title }}</h2>
            <p class="summary">{{ novel.summary || "还没有简介" }}</p>
            <div class="meta">
              <span>{{ novel.word_count }} 字</span>
              <span>{{ novel.chapter_count }} 章</span>
              <span>{{ novel.worlds.map((row) => row.name).join("、") || "未关联世界" }}</span>
            </div>
          </div>
          <div class="card-menu" @click.stop>
            <button class="icon-button" type="button" aria-label="小说设置" @click="menuKey = menuKey === novel.id ? '' : novel.id">⋯</button>
            <div v-if="menuKey === novel.id" class="menu-list">
              <button type="button" @click="openEditNovel(novel)">编辑</button>
              <button type="button" @click="duplicate(novel)">复制</button>
              <a :href="`/api/novels/${novel.id}/export.txt`">导出</a>
              <button v-if="novel.group_id" type="button" @click="leaveGroup(novel)">移出分类</button>
              <button class="danger" type="button" @click="removeNovel(novel)">删除</button>
            </div>
          </div>
        </article>
      </div>
    </section>

    <section v-else>
      <div v-if="!loading && worlds.length === 0" class="empty">还没有世界。</div>
      <div v-else class="book-shelf">
        <article v-for="world in worlds" :key="world.id" class="resource-card" @click="router.push(`/worlds/${world.id}/overview`)">
          <img class="book-cover" :src="coverSrc(world.cover_url, 'world')" alt="" />
          <div class="book-copy">
            <h2>{{ world.name }}</h2>
            <p class="summary">{{ world.summary || "还没有介绍" }}</p>
            <div class="meta"><span>{{ world.novel_count }} 本小说</span></div>
          </div>
          <div class="card-menu" @click.stop>
            <button class="icon-button" type="button" aria-label="世界设置" @click="menuKey = menuKey === world.id ? '' : world.id">⋯</button>
            <div v-if="menuKey === world.id" class="menu-list">
              <button type="button" @click="openEditWorld(world)">编辑</button>
              <button class="danger" type="button" @click="removeWorld(world)">删除</button>
            </div>
          </div>
        </article>
      </div>
    </section>

    <NModal v-model:show="novelOpen" preset="card" :title="editingId ? '编辑小说' : '创建小说'" style="width: 640px">
      <NForm label-placement="top">
        <NFormItem label="名称"><NInput v-model:value="novelForm.title" /></NFormItem>
        <NFormItem label="简介"><NInput v-model:value="novelForm.summary" type="textarea" :autosize="{ minRows: 3, maxRows: 6 }" /></NFormItem>
        <NFormItem label="封面">
          <CoverField v-model="novelForm.cover_url" :choices="novelCovers" owner-kind="novel" :owner-id="editingId || ''" />
        </NFormItem>
        <NFormItem label="关联世界">
          <div class="pick-list">
            <button v-for="world in worlds" :key="world.id" type="button" :class="{ on: novelForm.world_ids.includes(world.id) }" @click="toggleId(novelForm.world_ids, world.id)">{{ world.name }}</button>
            <span v-if="worlds.length === 0" class="muted">还没有世界</span>
          </div>
        </NFormItem>
        <NFormItem label="关联角色">
          <div class="pick-list">
            <button v-for="row in characters" :key="row.id" type="button" :class="{ on: novelForm.character_ids.includes(row.id) }" @click="toggleId(novelForm.character_ids, row.id)">{{ row.name }}</button>
            <span v-if="characters.length === 0" class="muted">还没有角色</span>
          </div>
        </NFormItem>
      </NForm>
      <template #footer>
        <NButton type="primary" @click="saveNovel">保存</NButton>
      </template>
    </NModal>

    <NModal v-model:show="worldOpen" preset="card" :title="worldForm.id ? '编辑世界' : '创建世界'" style="width: 640px">
      <NForm label-placement="top">
        <NFormItem label="名称"><NInput v-model:value="worldForm.name" /></NFormItem>
        <NFormItem label="介绍"><NInput v-model:value="worldForm.summary" type="textarea" :autosize="{ minRows: 3, maxRows: 6 }" /></NFormItem>
        <NFormItem label="图片">
          <CoverField v-model="worldForm.cover_url" :choices="worldCovers" owner-kind="world" :owner-id="worldForm.id" />
        </NFormItem>
      </NForm>
      <template #footer>
        <NButton type="primary" @click="saveWorld">保存</NButton>
      </template>
    </NModal>

    <NModal v-model:show="groupOpen" preset="card" :title="editingGroupId ? '修改分类' : '添加分类'" style="width: 420px">
      <NFormItem label="分类名称"><NInput v-model:value="groupName" /></NFormItem>
      <template #footer>
        <NButton type="primary" @click="saveGroup">保存</NButton>
      </template>
    </NModal>
  </main>
</template>
