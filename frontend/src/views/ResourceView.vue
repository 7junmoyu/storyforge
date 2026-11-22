<script setup lang="ts">
import { NButton, NForm, NFormItem, NInput, NSelect, useDialog, useMessage } from "naive-ui"
import { computed, ref, watch } from "vue"
import { RouterLink, useRoute } from "vue-router"
import { api } from "../api"
import type { AttributeTemplate, Character, CharacterPeriod, CharacterVersion, MediaAsset, Novel, ResourceLink, World, WorldRecord } from "../types"

const route = useRoute()
const message = useMessage()
const dialog = useDialog()
const world = ref<{ id: string; name: string; summary: string; novels: { id: string; title: string }[]; characters: ResourceLink[] } | null>(null)
const character = ref<Character | null>(null)
const characterWorlds = ref<ResourceLink[]>([])
const supplement = ref("")
const showGlobal = ref(false)
const linkScope = ref<"global" | "novel">("global")
const linkSource = ref("手动")
const linkNovelId = ref<string | null>(null)
const novels = ref<Novel[]>([])
const worlds = ref<World[]>([])
const characters = ref<Character[]>([])
const draftName = ref("")
const draftSummary = ref("")
const pickedWorld = ref<string | null>(null)
const pickedCharacter = ref<string | null>(null)
const linkNote = ref("")
const periods = ref<CharacterPeriod[]>([])
const versions = ref<CharacterVersion[]>([])
const activeVersion = ref<CharacterVersion | null>(null)
const periodName = ref("")
const periodRange = ref("")
const periodKey = ref("")
const periodValue = ref("")
const periodAttrs = ref<{ key: string; value: string }[]>([])
const editingPeriodId = ref("")
const versionName = ref("")
const versionSummary = ref("")
const versionKey = ref("")
const versionValue = ref("")
const versionAttrs = ref<{ key: string; value: string }[]>([])
const pickedPeriod = ref<string | null>(null)

const kind = computed(() => (route.path.startsWith("/worlds/") ? "world" : "character"))
const section = computed(() => String(route.params.section || "overview"))
const resourceId = computed(() => String(kind.value === "world" ? route.params.worldId : route.params.characterId))
const from = computed(() => (typeof route.query.from === "string" ? route.query.from : ""))
const later = new Set(["map", "relations", "ai"])
const recordKinds: Record<string, WorldRecord["kind"]> = { objects: "object", factions: "faction", places: "place", timeline: "event" }
const recordKind = computed(() => recordKinds[section.value] || "")
const records = ref<WorldRecord[]>([])
const assets = ref<MediaAsset[]>([])
const templates = ref<AttributeTemplate[]>([])
const globalAttrs = ref<{ key: string; value: string }[]>([])
const attrKey = ref("")
const attrValue = ref("")
const recordName = ref("")
const recordSummary = ref("")
const recordTime = ref("")
const editingRecordId = ref("")
const pickedTemplate = ref<string | null>(null)
const assetNote = ref("")
const sourceNovelId = computed(() => from.value.match(/^\/novels\/([0-9a-f-]{36})\//i)?.[1] ?? "")
const sourceWorldId = computed(() => from.value.match(/^\/worlds\/([0-9a-f-]{36})\//i)?.[1] ?? "")
const sourceNovel = computed(() => novels.value.find((item) => item.id === sourceNovelId.value) || null)
const currentWorldLink = computed(() => characterWorlds.value.find((row) => row.id === sourceWorldId.value) || null)

function linkText(row: ResourceLink) {
  const scope = row.scope === "novel" ? `小说内《${row.novel_title || "未指定"}》` : "全局"
  const time = row.created_at ? new Date(row.created_at).toLocaleDateString() : ""
  return [scope, row.source ? `来源 ${row.source}` : "", time, row.note || "没有说明"].filter(Boolean).join(" · ")
}
const scopeOptions = [
  { label: "全局关联", value: "global" },
  { label: "某本小说内的关联", value: "novel" },
]
const novelOptions = computed(() => novels.value.map((item) => ({ label: item.title, value: item.id })))
const periodOptions = computed(() => periods.value.map((item) => ({ label: item.name, value: item.id })))

const worldOptions = computed(() => worlds.value.map((item) => ({ label: item.name, value: item.id })))
const characterOptions = computed(() => characters.value.map((item) => ({ label: item.name, value: item.id })))
const templateOptions = computed(() => templates.value.map((item) => ({ label: item.name, value: item.id })))
const visibleRecords = computed(() => records.value.filter((row) => row.kind === recordKind.value))
const recordTitle = computed(() => ({ object: "对象", faction: "势力", place: "地点", event: "事件" })[recordKind.value] || "记录")

async function load() {
  if (kind.value === "world") {
    world.value = await api.worldRelations(resourceId.value)
    draftName.value = world.value.name
    draftSummary.value = world.value.summary
    characters.value = await api.characters()
    novels.value = await api.novels(true)
    records.value = await api.worldRecords(resourceId.value)
    supplement.value = sourceNovelId.value ? (await api.worldSetting(resourceId.value, sourceNovelId.value)).supplement : ""
    if (sourceNovelId.value) {
      linkScope.value = "novel"
      linkNovelId.value = sourceNovelId.value
      linkSource.value = "从小说进入"
    }
  } else {
    characters.value = await api.characters()
    character.value = characters.value.find((item) => item.id === resourceId.value) || null
    if (!character.value) throw new Error("角色不存在")
    draftName.value = character.value.name
    draftSummary.value = character.value.summary
    globalAttrs.value = Object.entries(character.value.attributes || {}).map(([key, value]) => ({ key, value }))
    assets.value = await api.assets("character", resourceId.value)
    templates.value = await api.templates()
    characterWorlds.value = await api.characterWorlds(resourceId.value)
    worlds.value = await api.worlds()
    novels.value = await api.novels(true)
    periods.value = await api.periods(resourceId.value)
    versions.value = await api.versions(resourceId.value)
    const current = versions.value.find((item) => item.novel_id === sourceNovelId.value) || null
    activeVersion.value = current
    versionName.value = current?.name || character.value.name
    versionSummary.value = current?.summary || ""
    versionAttrs.value = Object.entries(current?.attributes || {}).map(([key, value]) => ({ key, value }))
    if (sourceNovelId.value) {
      linkScope.value = "novel"
      linkNovelId.value = sourceNovelId.value
      linkSource.value = "从小说进入"
    }
  }
}

function attrsOf(rows: { key: string; value: string }[]) {
  return Object.fromEntries(rows.filter((row) => row.key.trim()).map((row) => [row.key.trim(), row.value]))
}

async function savePeriod() {
  if (!character.value || !periodName.value.trim()) return
  const body = { name: periodName.value.trim(), time_range: periodRange.value.trim(), attributes: attrsOf(periodAttrs.value) }
  if (editingPeriodId.value) await api.updatePeriod(editingPeriodId.value, body)
  else await api.createPeriod(character.value.id, body)
  periodName.value = ""
  periodRange.value = ""
  periodAttrs.value = []
  editingPeriodId.value = ""
  message.success("已保存全局角色时期")
  await load()
}

function editPeriod(row: CharacterPeriod) {
  editingPeriodId.value = row.id
  periodName.value = row.name
  periodRange.value = row.time_range
  periodAttrs.value = Object.entries(row.attributes).map(([key, value]) => ({ key, value }))
}

async function removePeriod(id: string) {
  await api.deletePeriod(id)
  await load()
}

async function saveVersion() {
  if (!character.value || !sourceNovelId.value || !versionName.value.trim()) return
  activeVersion.value = await api.saveVersion(character.value.id, sourceNovelId.value, {
    name: versionName.value.trim(),
    summary: versionSummary.value,
    attributes: attrsOf(versionAttrs.value),
    period_id: activeVersion.value?.period_id || null,
  })
  message.success("已保存这本小说的专属版本，其他小说没有改动")
  await load()
}

function copyGlobal() {
  if (!character.value || !sourceNovelId.value) return
  dialog.warning({
    title: "用全局档案覆盖本书版本",
    content: "只会改这本小说的专属版本。其他小说的版本和全局时期保持原样。",
    positiveText: "确认覆盖",
    negativeText: "取消",
    onPositiveClick: async () => {
      activeVersion.value = await api.versionFromGlobal(character.value!.id, sourceNovelId.value, true)
      message.success("已写入本书专属版本")
      await load()
    },
  })
}

async function copyPeriod() {
  if (!character.value || !sourceNovelId.value || !pickedPeriod.value) return
  activeVersion.value = await api.versionFromPeriod(character.value.id, sourceNovelId.value, pickedPeriod.value)
  message.success("已按所选时期写入本书专属版本")
  await load()
}

async function saveProfile() {
  if (kind.value === "world" && world.value) {
    const current = world.value
    dialog.warning({
      title: "保存全局世界设定",
      content: "这会改所有小说都能看到的基础档案，不会改写各小说自己的补充设定。",
      positiveText: "确认保存",
      negativeText: "取消",
      onPositiveClick: async () => {
        await api.updateWorld(current.id, { name: draftName.value, summary: draftSummary.value })
        message.success("已保存全局世界基础设定")
        await load()
      },
    })
    return
  }
  if (character.value) {
    await api.updateCharacter(character.value.id, { name: draftName.value, summary: draftSummary.value, attributes: attrsOf(globalAttrs.value) })
    message.success("已保存全局角色基础档案，已有的小说专属版本没有被覆盖")
  }
  await load()
}

async function saveSupplement() {
  if (!world.value || !sourceNovelId.value) return
  await api.saveWorldSetting(world.value.id, sourceNovelId.value, supplement.value)
  message.success("已保存这本小说的世界补充，全局设定没有改动")
}

function linkBody(worldId: string) {
  return {
    world_id: worldId,
    note: linkNote.value,
    scope: linkScope.value,
    source: linkSource.value || "手动",
    novel_id: linkScope.value === "novel" ? linkNovelId.value : null,
  }
}

function editLink(row: ResourceLink, worldId: string, characterId: string) {
  pickedWorld.value = worldId
  pickedCharacter.value = characterId
  linkNote.value = row.note
  linkScope.value = row.scope
  linkSource.value = row.source
  linkNovelId.value = row.novel_id
}

async function addCharacterToWorld() {
  if (!world.value || !pickedCharacter.value) return
  await api.linkCharacterWorld(pickedCharacter.value, linkBody(world.value.id))
  linkNote.value = ""
  message.success("已保存角色和世界的关联，没有改角色档案")
  await load()
}

async function addWorldToCharacter() {
  if (!character.value || !pickedWorld.value) return
  await api.linkCharacterWorld(character.value.id, linkBody(pickedWorld.value))
  linkNote.value = ""
  message.success("已保存角色和世界的关联，没有改角色档案")
  await load()
}

async function saveRecord() {
  if (!world.value || !recordKind.value || !recordName.value.trim()) return
  const body = { name: recordName.value.trim(), summary: recordSummary.value.trim(), time_label: recordTime.value.trim() }
  if (editingRecordId.value) await api.updateWorldRecord(editingRecordId.value, body)
  else await api.createWorldRecord(world.value.id, { kind: recordKind.value, ...body })
  recordName.value = ""
  recordSummary.value = ""
  recordTime.value = ""
  editingRecordId.value = ""
  message.success("已保存")
  await load()
}

function editRecord(row: WorldRecord) {
  editingRecordId.value = row.id
  recordName.value = row.name
  recordSummary.value = row.summary
  recordTime.value = row.time_label
}

async function removeRecord(id: string) {
  await api.deleteWorldRecord(id)
  await load()
}

function applyTemplate() {
  if (!character.value || !pickedTemplate.value) return
  const templateId = pickedTemplate.value
  dialog.warning({
    title: "用模板补充空字段",
    content: "只会补上还没有内容的字段。已经填写的属性保持原样，其他小说的专属版本也不会被改。",
    positiveText: "确认补充",
    negativeText: "取消",
    onPositiveClick: async () => {
      const updated = await api.applyTemplate(character.value!.id, templateId)
      globalAttrs.value = Object.entries(updated.attributes || {}).map(([key, value]) => ({ key, value }))
      message.success("已补充空字段")
    },
  })
}

async function onAsset(event: Event) {
  const input = event.target as HTMLInputElement
  const file = input.files?.[0]
  if (!file || !character.value) return
  await api.uploadAsset(file, "character", character.value.id, assetNote.value)
  assetNote.value = ""
  input.value = ""
  message.success("已上传素材")
  assets.value = await api.assets("character", character.value.id)
}

async function removeAsset(id: string) {
  await api.deleteAsset(id)
  if (character.value) assets.value = await api.assets("character", character.value.id)
}

async function unlink(characterId: string, worldId: string) {
  await api.unlinkCharacterWorld(characterId, worldId)
  message.success("已解除关联，资源本身还在")
  await load()
}

const appearedNovels = computed(() => novels.value.filter((novel) => novel.characters.some((item) => item.id === resourceId.value)))

watch(() => [resourceId.value, kind.value, from.value], () => {
  void load().catch((error: unknown) => message.error(error instanceof Error ? error.message : "加载失败"))
}, { immediate: true })
</script>

<template>
  <main class="page">
    <p v-if="from" class="muted">从小说工作空间进入 · <RouterLink :to="from">返回来源</RouterLink></p>
    <header class="workspace-head">
      <div>
        <h1>{{ kind === "world" ? world?.name : character?.name }}</h1>
        <p class="muted">{{ kind === "world" ? "世界工作区" : sourceNovel ? `角色工作区 · 当前小说《${sourceNovel.title}》` : "角色工作区 · 全局基础资料" }}</p>
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
      <article v-if="character" class="card stat"><strong>{{ periods.length }}</strong><span>角色时期</span></article>
      <article class="card library-card">
        <p>{{ (world?.summary || character?.summary) || "还没有介绍" }}</p>
        <p v-if="world && sourceNovel" class="muted">《{{ sourceNovel.title }}》的补充：{{ supplement || "还没有只属于这本小说的补充。" }}</p>
        <p v-if="currentWorldLink" class="muted">当前世界关联：{{ linkText(currentWorldLink) }}</p>
      </article>
    </section>

    <section v-else-if="section === 'setting' || section === 'profile'" class="panel" style="padding: 24px">
      <div v-if="world && sourceNovelId">
        <h2>本书补充设定</h2>
        <p class="muted">只属于《{{ sourceNovel?.title || "当前小说" }}》。保存这里不会改全局世界设定，其他小说也看不到这段补充。</p>
        <NInput v-model:value="supplement" type="textarea" :autosize="{ minRows: 4, maxRows: 8 }" />
        <NButton type="primary" style="margin-top: 12px" @click="saveSupplement">保存本书补充</NButton>
      </div>
      <div v-if="character && sourceNovelId" style="margin-bottom: 28px">
        <h2>本书专属版本</h2>
        <p class="muted">这份资料只属于《{{ sourceNovel?.title || "当前小说" }}》。取消确认不会写入。</p>
        <div class="actions" style="margin: 12px 0">
          <NButton @click="copyGlobal">{{ activeVersion ? "用全局档案覆盖本书" : "从全局档案建立" }}</NButton>
          <NSelect v-model:value="pickedPeriod" :options="periodOptions" placeholder="选择一个时期" style="width: 180px" />
          <NButton @click="copyPeriod">按时期写入本书</NButton>
        </div>
        <NForm v-if="activeVersion" label-placement="top">
          <NFormItem label="本书中的名称"><NInput v-model:value="versionName" /></NFormItem>
          <NFormItem label="本书中的介绍"><NInput v-model:value="versionSummary" type="textarea" :autosize="{ minRows: 3, maxRows: 6 }" /></NFormItem>
          <NFormItem label="本书属性">
            <div>
              <p v-for="(row, index) in versionAttrs" :key="index" class="meta">{{ row.key }}：{{ row.value }} <button class="text-button" type="button" @click="versionAttrs.splice(index, 1)">移除</button></p>
              <div class="actions">
                <NInput v-model:value="versionKey" placeholder="属性" style="max-width: 140px" />
                <NInput v-model:value="versionValue" placeholder="内容" style="max-width: 220px" />
                <NButton @click="versionAttrs.push({ key: versionKey, value: versionValue }); versionKey = ''; versionValue = ''">添加</NButton>
              </div>
            </div>
          </NFormItem>
        </NForm>
        <NButton v-if="activeVersion" type="primary" @click="saveVersion">保存本书版本</NButton>
        <button class="text-button" type="button" style="margin-left: 12px" @click="showGlobal = !showGlobal">{{ showGlobal ? "收起全局档案" : "查看全局档案" }}</button>
      </div>
      <div v-if="kind === 'world' || !sourceNovelId || showGlobal">
        <h2 v-if="sourceNovel">全局基础资料</h2>
        <p class="muted">{{ kind === "world" ? "保存前会再确认一次。全局设定会给所有使用这个世界的小说看到，不会改各小说的补充。" : "保存全局档案不会覆盖已经存在的小说专属版本。" }}</p>
        <NForm label-placement="top">
          <NFormItem label="名称"><NInput v-model:value="draftName" /></NFormItem>
          <NFormItem label="介绍"><NInput v-model:value="draftSummary" type="textarea" :autosize="{ minRows: 4, maxRows: 8 }" /></NFormItem>
          <NFormItem v-if="kind === 'character'" label="全局属性">
            <div>
              <p v-for="(row, index) in globalAttrs" :key="index" class="meta">{{ row.key }}：{{ row.value || "空" }} <button class="text-button" type="button" @click="globalAttrs.splice(index, 1)">移除</button></p>
              <div class="actions">
                <NInput v-model:value="attrKey" placeholder="属性" style="max-width: 140px" />
                <NInput v-model:value="attrValue" placeholder="内容" style="max-width: 220px" />
                <NButton @click="globalAttrs.push({ key: attrKey, value: attrValue }); attrKey = ''; attrValue = ''">添加</NButton>
              </div>
            </div>
          </NFormItem>
        </NForm>
        <div v-if="kind === 'character'" class="actions" style="margin-bottom: 12px">
          <NSelect v-model:value="pickedTemplate" :options="templateOptions" placeholder="选择属性模板" style="width: 180px" />
          <NButton @click="applyTemplate">用模板补充空字段</NButton>
        </div>
        <NButton :type="sourceNovel && kind === 'character' ? 'default' : 'primary'" @click="saveProfile">保存全局{{ kind === "world" ? "设定" : "档案" }}</NButton>
      </div>
      <div v-if="character && versions.length" style="margin-top: 24px">
        <h2>其他小说中的版本</h2>
        <article v-for="row in versions.filter((item) => item.novel_id !== sourceNovelId)" :key="row.id" class="row-card">
          <div>
            <strong>{{ row.novel_title }}</strong>
            <p class="muted">{{ row.name }} · {{ row.summary || "没有专属介绍" }}</p>
          </div>
          <RouterLink class="text-button" :to="{ path: `/characters/${character.id}/profile`, query: { from: `/novels/${row.novel_id}/characters` } }">查看</RouterLink>
        </article>
      </div>
    </section>

    <section v-else-if="kind === 'character' && section === 'periods'" class="panel" style="padding: 24px">
      <p class="muted">时期属于全局角色。把它写入某本小说时，只会生成那本小说自己的专属版本。</p>
      <article v-for="row in periods" :key="row.id" class="row-card">
        <div>
          <strong>{{ row.name }}</strong>
          <p class="muted">{{ row.time_range || "未填写时间范围" }}</p>
        </div>
        <div class="actions">
          <button class="text-button" type="button" @click="editPeriod(row)">编辑</button>
          <button class="text-button danger" type="button" @click="removePeriod(row.id)">删除</button>
        </div>
      </article>
      <NForm label-placement="top">
        <NFormItem label="时期名称"><NInput v-model:value="periodName" placeholder="时期名称" /></NFormItem>
        <NFormItem label="时间范围"><NInput v-model:value="periodRange" placeholder="例如少年、远航之后" /></NFormItem>
        <NFormItem label="时期属性">
          <div>
            <p v-for="(row, index) in periodAttrs" :key="index" class="meta">{{ row.key }}：{{ row.value }} <button class="text-button" type="button" @click="periodAttrs.splice(index, 1)">移除</button></p>
            <div class="actions">
              <NInput v-model:value="periodKey" placeholder="属性" style="max-width: 140px" />
              <NInput v-model:value="periodValue" placeholder="内容" style="max-width: 220px" />
              <NButton @click="periodAttrs.push({ key: periodKey, value: periodValue }); periodKey = ''; periodValue = ''">添加</NButton>
            </div>
          </div>
        </NFormItem>
      </NForm>
      <NButton type="primary" @click="savePeriod">{{ editingPeriodId ? "保存时期" : "添加时期" }}</NButton>
    </section>

    <section v-else-if="recordKind && world" class="panel" style="padding: 24px">
      <p class="muted">这些资料属于当前世界。这里只保存名称和说明，对象之间的关系图和地图以后再做。</p>
      <article v-for="row in visibleRecords" :key="row.id" class="row-card">
        <div>
          <strong>{{ row.name }}</strong>
          <p class="muted">{{ row.time_label }} {{ row.summary || "还没有说明" }}</p>
        </div>
        <div class="actions">
          <button class="text-button" type="button" @click="editRecord(row)">编辑</button>
          <button class="text-button danger" type="button" @click="removeRecord(row.id)">删除</button>
        </div>
      </article>
      <NForm label-placement="top">
        <NFormItem :label="`${recordTitle}名称`"><NInput v-model:value="recordName" /></NFormItem>
        <NFormItem v-if="recordKind === 'event'" label="时间"><NInput v-model:value="recordTime" placeholder="例如远航之后、第三年春" /></NFormItem>
        <NFormItem label="说明"><NInput v-model:value="recordSummary" type="textarea" :autosize="{ minRows: 3, maxRows: 6 }" /></NFormItem>
      </NForm>
      <NButton type="primary" @click="saveRecord">{{ editingRecordId ? "保存" : `添加${recordTitle}` }}</NButton>
    </section>

    <section v-else-if="kind === 'character' && section === 'assets' && character" class="panel" style="padding: 24px">
      <p class="muted">这里保存这个角色的参考图片。生成图片以后再做。</p>
      <article v-for="row in assets" :key="row.id" class="row-card">
        <div>
          <img :src="row.url" :alt="row.filename" style="max-width: 160px; display: block" />
          <p class="muted">{{ row.note || row.filename }}</p>
        </div>
        <button class="text-button danger" type="button" @click="removeAsset(row.id)">删除</button>
      </article>
      <div class="actions">
        <NInput v-model:value="assetNote" placeholder="这张图用来做什么" style="max-width: 220px" />
        <input type="file" accept="image/jpeg,image/png,image/gif,image/webp" @change="onAsset" />
      </div>
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
        <NSelect v-model:value="pickedCharacter" :options="characterOptions" placeholder="选择全局角色" style="width: 180px" />
        <NSelect v-model:value="linkScope" :options="scopeOptions" style="width: 180px" />
        <NSelect v-if="linkScope === 'novel'" v-model:value="linkNovelId" :options="novelOptions" placeholder="哪本小说" style="width: 160px" />
        <NInput v-model:value="linkSource" placeholder="来源" style="max-width: 120px" />
        <NInput v-model:value="linkNote" placeholder="关联说明" style="max-width: 180px" />
        <NButton @click="addCharacterToWorld">保存关联</NButton>
      </div>
      <article v-for="row in world.characters" :key="row.id" class="card row-card">
        <div>
          <RouterLink :to="{ path: `/characters/${row.id}/overview`, query: from ? { from } : {} }">{{ row.name }}</RouterLink>
          <p class="muted">{{ linkText(row) }}</p>
        </div>
        <div class="actions">
          <button class="text-button" type="button" @click="editLink(row, world.id, row.id)">编辑</button>
          <button class="text-button danger" type="button" @click="unlink(row.id, world.id)">解除关联</button>
        </div>
      </article>
    </section>

    <section v-else-if="kind === 'character' && section === 'worlds' && character">
      <div class="actions" style="margin-bottom: 12px">
        <NSelect v-model:value="pickedWorld" :options="worldOptions" placeholder="选择世界" style="width: 180px" />
        <NSelect v-model:value="linkScope" :options="scopeOptions" style="width: 180px" />
        <NSelect v-if="linkScope === 'novel'" v-model:value="linkNovelId" :options="novelOptions" placeholder="哪本小说" style="width: 160px" />
        <NInput v-model:value="linkSource" placeholder="来源" style="max-width: 120px" />
        <NInput v-model:value="linkNote" placeholder="关联说明" style="max-width: 180px" />
        <NButton @click="addWorldToCharacter">保存关联</NButton>
      </div>
      <article v-for="row in characterWorlds" :key="row.id" class="card row-card">
        <div>
          <RouterLink :to="{ path: `/worlds/${row.id}/overview`, query: from ? { from } : {} }">{{ row.name }}</RouterLink>
          <p class="muted">{{ linkText(row) }}</p>
        </div>
        <div class="actions">
          <button class="text-button" type="button" @click="editLink(row, row.id, character.id)">编辑</button>
          <button class="text-button danger" type="button" @click="unlink(character.id, row.id)">解除关联</button>
        </div>
      </article>
    </section>
  </main>
</template>
