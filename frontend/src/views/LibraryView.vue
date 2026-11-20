<script setup lang="ts">
import { NButton, NForm, NFormItem, NInput, useDialog, useMessage } from "naive-ui"
import { computed, onMounted, reactive, ref, watch } from "vue"
import { useRoute, useRouter } from "vue-router"
import { api } from "../api"
import type { Character } from "../types"

const route = useRoute()
const router = useRouter()
const message = useMessage()
const dialog = useDialog()
const configured = ref(false)
const model = ref("")
const base = ref("")
const query = ref("")
const characters = ref<Character[]>([])
const form = reactive({ id: "", name: "", summary: "" })
const isSettings = computed(() => route.path === "/settings")

async function loadCharacters() {
  characters.value = await api.characters(query.value)
}

async function saveCharacter() {
  if (!form.name.trim()) return
  if (form.id) await api.updateCharacter(form.id, { name: form.name, summary: form.summary })
  else await api.createCharacter({ name: form.name, summary: form.summary })
  form.id = ""
  form.name = ""
  form.summary = ""
  await loadCharacters()
}

function editCharacter(row: Character) {
  Object.assign(form, row)
}

function removeCharacter(row: Character) {
  dialog.warning({
    title: "删除角色",
    content: `删除「${row.name}」。如果还有小说、大纲或伏笔使用它，删除会被拒绝。`,
    positiveText: "删除",
    negativeText: "取消",
    onPositiveClick: async () => {
      try {
        await api.deleteCharacter(row.id)
        await loadCharacters()
      } catch (error) {
        message.error(error instanceof Error ? error.message : "删除失败")
      }
    },
  })
}

onMounted(async () => {
  const settings = await api.settings()
  configured.value = settings.ai_configured
  model.value = settings.ai_model
  base.value = settings.ai_base_url
  if (!isSettings.value) await loadCharacters()
})
watch(isSettings, () => {
  if (!isSettings.value) void loadCharacters()
})
</script>

<template>
  <main class="page">
    <header class="workspace-head">
      <div>
        <h1>{{ $route.path === "/settings" ? "设置" : "角色库" }}</h1>
      </div>
    </header>
    <section v-if="$route.path === '/settings'" class="panel" style="padding: 18px">
      <p>主题可以在左侧底部切换，选择会留在这台浏览器里。</p>
      <p class="muted">模型接口：{{ base }}</p>
      <p class="muted">模型：{{ model }}</p>
      <p>{{ configured ? "已配置 API 密钥。写作建议会请求这个模型。" : "还没有 API 密钥，写作、大纲和伏笔建议使用本地示例。密钥写在项目根目录的 .env 里，页面不保存密钥。" }}</p>
    </section>
    <section v-else class="split">
      <div>
        <div class="actions" style="margin-bottom: 12px">
          <NInput v-model:value="query" placeholder="搜索角色" style="max-width: 220px" @keyup.enter="loadCharacters" />
          <NButton size="small" @click="loadCharacters">搜索</NButton>
        </div>
        <p v-if="characters.length === 0" class="empty">还没有角色。角色是全局资源，不跟着某一本小说删除。</p>
        <article v-for="row in characters" :key="row.id" class="card row-card">
          <div>
            <strong>{{ row.name }}</strong>
            <p class="summary">{{ row.summary || "还没有介绍" }}</p>
            <div class="meta"><span>{{ row.novel_count }} 本小说</span></div>
          </div>
          <div class="actions">
            <NButton size="small" type="primary" @click="router.push(`/characters/${row.id}/overview`)">查看</NButton>
            <button class="text-button" type="button" @click="editCharacter(row)">编辑</button>
            <button class="text-button danger" type="button" @click="removeCharacter(row)">删除</button>
          </div>
        </article>
      </div>
      <div class="panel" style="padding: 16px">
        <NForm label-placement="top">
          <NFormItem label="姓名"><NInput v-model:value="form.name" /></NFormItem>
          <NFormItem label="基础介绍"><NInput v-model:value="form.summary" type="textarea" :autosize="{ minRows: 4, maxRows: 8 }" /></NFormItem>
        </NForm>
        <p class="muted">这里只维护全局基础档案。时期、小说专属版本和关系图留在后续阶段。删除角色不会删除小说。</p>
        <div class="actions">
          <NButton type="primary" @click="saveCharacter">{{ form.id ? "保存" : "创建角色" }}</NButton>
          <NButton v-if="form.id" @click="form.id = ''; form.name = ''; form.summary = ''">取消编辑</NButton>
        </div>
      </div>
    </section>
  </main>
</template>
