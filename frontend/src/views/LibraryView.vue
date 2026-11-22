<script setup lang="ts">
import { NButton, NForm, NFormItem, NInput, useDialog, useMessage } from "naive-ui"
import { computed, onMounted, reactive, ref, watch } from "vue"
import { useRoute, useRouter } from "vue-router"
import { api } from "../api"
import CoverField from "../components/CoverField.vue"
import { characterCovers, coverSrc } from "../covers"
import type { AttributeTemplate, Character } from "../types"

const route = useRoute()
const router = useRouter()
const message = useMessage()
const dialog = useDialog()
const configured = ref(false)
const model = ref("")
const base = ref("")
const query = ref("")
const characters = ref<Character[]>([])
const form = reactive({ id: "", name: "", summary: "", cover_url: characterCovers[0].url })
const templates = ref<AttributeTemplate[]>([])
const templateName = ref("")
const templateFields = ref("")
const menuKey = ref("")
const isSettings = computed(() => route.path === "/settings")

async function loadCharacters() {
  characters.value = await api.characters(query.value)
}

async function saveCharacter() {
  if (!form.name.trim()) return
  const body = { name: form.name, summary: form.summary, cover_url: form.cover_url }
  if (form.id) await api.updateCharacter(form.id, body)
  else await api.createCharacter(body)
  form.id = ""
  form.name = ""
  form.summary = ""
  form.cover_url = characterCovers[0].url
  await loadCharacters()
}

function editCharacter(row: Character) {
  menuKey.value = ""
  Object.assign(form, { id: row.id, name: row.name, summary: row.summary, cover_url: row.cover_url || characterCovers[0].url })
}

function removeCharacter(row: Character) {
  menuKey.value = ""
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

async function loadTemplates() {
  templates.value = await api.templates()
}

async function saveTemplate() {
  const fields = templateFields.value.split(/[,，]/).map((item) => item.trim()).filter(Boolean)
  if (!templateName.value.trim() || fields.length === 0) return
  await api.createTemplate({ name: templateName.value.trim(), fields })
  templateName.value = ""
  templateFields.value = ""
  await loadTemplates()
}

async function removeTemplate(id: string) {
  await api.deleteTemplate(id)
  await loadTemplates()
}

onMounted(async () => {
  const settings = await api.settings()
  configured.value = settings.ai_configured
  model.value = settings.ai_model
  base.value = settings.ai_base_url
  if (isSettings.value) await loadTemplates()
  else await loadCharacters()
})
watch(isSettings, () => {
  if (isSettings.value) void loadTemplates()
  else void loadCharacters()
})
</script>

<template>
  <main class="page" @click="menuKey = ''">
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
      <h2>角色属性模板</h2>
      <p class="muted">模板只定义字段名称。用到角色上时，只会补还是空的字段，不会改已经写过的内容，也不会改小说专属版本。</p>
      <article v-for="row in templates" :key="row.id" class="row-card">
        <div>
          <strong>{{ row.name }}</strong>
          <p class="muted">{{ row.fields.join("、") }}</p>
        </div>
        <button class="text-button danger" type="button" @click="removeTemplate(row.id)">删除</button>
      </article>
      <div class="actions">
        <NInput v-model:value="templateName" placeholder="模板名称" style="max-width: 160px" />
        <NInput v-model:value="templateFields" placeholder="字段用逗号分开，例如身份、年龄" style="max-width: 280px" />
        <NButton type="primary" @click="saveTemplate">添加模板</NButton>
      </div>
    </section>
    <section v-else class="split">
      <div>
        <div class="actions" style="margin-bottom: 12px">
          <NInput v-model:value="query" placeholder="搜索角色" style="max-width: 220px" @keyup.enter="loadCharacters" />
          <NButton size="small" @click="loadCharacters">搜索</NButton>
        </div>
        <p v-if="characters.length === 0" class="empty">还没有角色。角色是全局资源，不跟着某一本小说删除。</p>
        <div class="book-shelf">
          <article v-for="row in characters" :key="row.id" class="resource-card" @click="router.push(`/characters/${row.id}/overview`)">
            <img class="book-cover" :src="coverSrc(row.cover_url, 'character')" alt="" />
            <div class="book-copy">
              <h2>{{ row.name }}</h2>
              <p class="summary">{{ row.summary || "还没有介绍" }}</p>
              <div class="meta"><span>{{ row.novel_count }} 本小说</span></div>
            </div>
            <div class="card-menu" @click.stop>
              <button class="icon-button" type="button" aria-label="角色设置" @click="menuKey = menuKey === row.id ? '' : row.id">⋯</button>
              <div v-if="menuKey === row.id" class="menu-list">
                <button type="button" @click="editCharacter(row)">编辑</button>
                <button class="danger" type="button" @click="removeCharacter(row)">删除</button>
              </div>
            </div>
          </article>
        </div>
      </div>
      <div class="panel" style="padding: 16px">
        <NForm label-placement="top">
          <NFormItem label="姓名"><NInput v-model:value="form.name" /></NFormItem>
          <NFormItem label="基础介绍"><NInput v-model:value="form.summary" type="textarea" :autosize="{ minRows: 4, maxRows: 8 }" /></NFormItem>
          <NFormItem label="图片">
            <CoverField v-model="form.cover_url" :choices="characterCovers" owner-kind="character" :owner-id="form.id" />
          </NFormItem>
        </NForm>
        <p class="muted">这里只维护全局基础档案。时期、小说专属版本和关系图留在后续阶段。删除角色不会删除小说。</p>
        <div class="actions">
          <NButton type="primary" @click="saveCharacter">{{ form.id ? "保存" : "创建角色" }}</NButton>
          <NButton v-if="form.id" @click="form.id = ''; form.name = ''; form.summary = ''; form.cover_url = characterCovers[0].url">取消编辑</NButton>
        </div>
      </div>
    </section>
  </main>
</template>
