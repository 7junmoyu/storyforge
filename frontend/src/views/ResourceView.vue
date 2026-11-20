<script setup lang="ts">
import { NButton, NForm, NFormItem, NInput, NSelect, useMessage } from "naive-ui"
import { computed, ref, watch } from "vue"
import { RouterLink, useRoute } from "vue-router"
import { api } from "../api"
import type { Character, Novel, World } from "../types"

const route = useRoute()
const message = useMessage()
const world = ref<{ id: string; name: string; summary: string; novels: { id: string; title: string }[]; characters: { id: string; name: string; note: string }[] } | null>(null)
const character = ref<Character | null>(null)
const characterWorlds = ref<{ id: string; name: string; note: string }[]>([])
const novels = ref<Novel[]>([])
const worlds = ref<World[]>([])
const characters = ref<Character[]>([])
const draftName = ref("")
const draftSummary = ref("")
const pickedWorld = ref<string | null>(null)
const pickedCharacter = ref<string | null>(null)
const linkNote = ref("")

const kind = computed(() => (route.path.startsWith("/worlds/") ? "world" : "character"))
const section = computed(() => String(route.params.section || "overview"))
const resourceId = computed(() => String(kind.value === "world" ? route.params.worldId : route.params.characterId))
const from = computed(() => (typeof route.query.from === "string" ? route.query.from : ""))
const later = new Set(["objects", "map", "factions", "places", "timeline", "periods", "relations", "assets", "ai"])

const worldOptions = computed(() => worlds.value.map((item) => ({ label: item.name, value: item.id })))
const characterOptions = computed(() => characters.value.map((item) => ({ label: item.name, value: item.id })))

async function load() {
  if (kind.value === "world") {
    world.value = await api.worldRelations(resourceId.value)
    draftName.value = world.value.name
    draftSummary.value = world.value.summary
    characters.value = await api.characters()
  } else {
    characters.value = await api.characters()
    character.value = characters.value.find((item) => item.id === resourceId.value) || null
    if (!character.value) throw new Error("角色不存在")
    draftName.value = character.value.name
    draftSummary.value = character.value.summary
    characterWorlds.value = await api.characterWorlds(resourceId.value)
    worlds.value = await api.worlds()
    novels.value = await api.novels(true)
  }
}

async function saveProfile() {
  if (kind.value === "world" && world.value) {
    await api.updateWorld(world.value.id, { name: draftName.value, summary: draftSummary.value })
    message.success("已保存全局世界基础设定")
  } else if (character.value) {
    await api.updateCharacter(character.value.id, { name: draftName.value, summary: draftSummary.value })
    message.success("已保存全局角色基础档案")
  }
  await load()
}

async function addCharacterToWorld() {
  if (!world.value || !pickedCharacter.value) return
  await api.linkCharacterWorld(pickedCharacter.value, { world_id: world.value.id, note: linkNote.value })
  pickedCharacter.value = null
  linkNote.value = ""
  await load()
}

async function addWorldToCharacter() {
  if (!character.value || !pickedWorld.value) return
  await api.linkCharacterWorld(character.value.id, { world_id: pickedWorld.value, note: linkNote.value })
  pickedWorld.value = null
  linkNote.value = ""
  await load()
}

async function unlink(characterId: string, worldId: string) {
  await api.unlinkCharacterWorld(characterId, worldId)
  message.success("已解除关联，资源本身还在")
  await load()
}

const appearedNovels = computed(() => novels.value.filter((novel) => novel.characters.some((item) => item.id === resourceId.value)))

watch(() => [resourceId.value, kind.value], () => {
  void load().catch((error: unknown) => message.error(error instanceof Error ? error.message : "加载失败"))
}, { immediate: true })
</script>

<template>
  <main class="page">
    <p v-if="from" class="muted">从小说工作空间进入 · <RouterLink :to="from">返回来源</RouterLink></p>
    <header class="workspace-head">
      <div>
        <h1>{{ kind === "world" ? world?.name : character?.name }}</h1>
        <p class="muted">{{ kind === "world" ? "世界工作区" : "角色工作区" }} · 全局基础资料</p>
      </div>
    </header>

    <section v-if="later.has(section)" class="empty">
      这个模块留在后续阶段。当前工作区已经可以查看基础资料、关联小说和角色与世界的直接关系。地图编辑和角色聊天不在这里展开。
    </section>

    <section v-else-if="section === 'overview'" class="stats">
      <article v-if="world" class="card stat"><strong>{{ world.novels.length }}</strong><span>关联小说</span></article>
      <article v-if="world" class="card stat"><strong>{{ world.characters.length }}</strong><span>直接关联角色</span></article>
      <article v-if="character" class="card stat"><strong>{{ appearedNovels.length }}</strong><span>出场小说</span></article>
      <article v-if="character" class="card stat"><strong>{{ characterWorlds.length }}</strong><span>所属世界</span></article>
      <article class="card library-card">
        <p>{{ (world?.summary || character?.summary) || "还没有介绍" }}</p>
      </article>
    </section>

    <section v-else-if="section === 'setting' || section === 'profile'" class="panel" style="padding: 18px">
      <p class="muted">这里修改的是全局基础资料。已经关联的小说不会自动改掉各自的正文和专属设定。</p>
      <NForm label-placement="top">
        <NFormItem label="名称"><NInput v-model:value="draftName" /></NFormItem>
        <NFormItem label="介绍"><NInput v-model:value="draftSummary" type="textarea" :autosize="{ minRows: 4, maxRows: 8 }" /></NFormItem>
      </NForm>
      <NButton type="primary" @click="saveProfile">保存基础资料</NButton>
    </section>

    <section v-else-if="section === 'novels'">
      <article v-for="novel in (world ? world.novels : appearedNovels)" :key="novel.id" class="card row-card">
        <strong>{{ "title" in novel ? novel.title : "" }}</strong>
        <RouterLink class="text-button" :to="`/novels/${novel.id}/overview`">进入小说</RouterLink>
      </article>
      <p v-if="(world ? world.novels.length : appearedNovels.length) === 0" class="empty">还没有关联小说。</p>
    </section>

    <section v-else-if="kind === 'world' && section === 'characters' && world">
      <div class="actions" style="margin-bottom: 12px">
        <NSelect v-model:value="pickedCharacter" :options="characterOptions" placeholder="选择全局角色" style="width: 220px" />
        <NInput v-model:value="linkNote" placeholder="关联说明" style="max-width: 220px" />
        <NButton @click="addCharacterToWorld">建立关联</NButton>
      </div>
      <article v-for="row in world.characters" :key="row.id" class="card row-card">
        <div>
          <RouterLink :to="{ path: `/characters/${row.id}/overview`, query: from ? { from } : {} }">{{ row.name }}</RouterLink>
          <p class="muted">{{ row.note || "直接关联" }}</p>
        </div>
        <NButton size="small" quaternary @click="unlink(row.id, world.id)">解除关联</NButton>
      </article>
    </section>

    <section v-else-if="kind === 'character' && section === 'worlds' && character">
      <div class="actions" style="margin-bottom: 12px">
        <NSelect v-model:value="pickedWorld" :options="worldOptions" placeholder="选择世界" style="width: 220px" />
        <NInput v-model:value="linkNote" placeholder="关联说明" style="max-width: 220px" />
        <NButton @click="addWorldToCharacter">建立关联</NButton>
      </div>
      <article v-for="row in characterWorlds" :key="row.id" class="card row-card">
        <div>
          <RouterLink :to="{ path: `/worlds/${row.id}/overview`, query: from ? { from } : {} }">{{ row.name }}</RouterLink>
          <p class="muted">{{ row.note || "直接关联" }}</p>
        </div>
        <NButton size="small" quaternary @click="unlink(character.id, row.id)">解除关联</NButton>
      </article>
    </section>
  </main>
</template>
