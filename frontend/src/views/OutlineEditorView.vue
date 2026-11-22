<script setup lang="ts">
import { NButton, NFormItem, NInput, NSelect, useMessage } from "naive-ui"
import { computed, reactive, ref, watch } from "vue"
import { useRoute, useRouter } from "vue-router"
import { api } from "../api"
import type { NovelDetail, OutlineNode } from "../types"

const route = useRoute()
const router = useRouter()
const message = useMessage()
const novel = ref<NovelDetail | null>(null)
const node = ref<OutlineNode | null>(null)
const saving = ref(false)
const suggestion = ref("")
const form = reactive({
  title: "",
  content: "",
  notes: "",
  status: "pending",
  world_id: null as string | null,
  character_ids: [] as string[],
})

const novelId = computed(() => String(route.params.novelId))
const nodeId = computed(() => String(route.params.nodeId))
const outlineStatus = [
  { label: "未开始", value: "pending" },
  { label: "进行中", value: "active" },
  { label: "已完成", value: "done" },
]
const worldOptions = computed(() => (novel.value?.worlds ?? []).map((row) => ({ label: row.name, value: row.id })))
const characterOptions = computed(() => (novel.value?.characters ?? []).map((row) => ({ label: row.name, value: row.id })))

async function load(expand = false) {
  const [detail, nodes] = await Promise.all([api.novel(novelId.value), api.outline(novelId.value)])
  novel.value = detail
  const found = nodes.find((item) => item.id === nodeId.value)
  if (!found) {
    message.error("大纲不存在")
    await router.replace(`/novels/${novelId.value}/outline`)
    return
  }
  node.value = found
  Object.assign(form, {
    title: found.title,
    content: found.content,
    notes: found.notes,
    status: found.status,
    world_id: found.world_id,
    character_ids: [...found.character_ids],
  })
  if (expand) {
    const result = await api.expandOutline(found.id)
    form.content = result.content
    suggestion.value = "扩展建议已放进正文，保存后才会写入。"
  }
}

async function save() {
  if (!node.value || !form.title.trim()) {
    message.warning("请填写标题")
    return
  }
  saving.value = true
  try {
    const saved = await api.updateOutline(node.value.id, {
      title: form.title,
      content: form.content,
      notes: form.notes,
      status: form.status,
      world_id: form.world_id,
      clear_world: form.world_id === null,
      character_ids: form.character_ids,
    })
    node.value = saved
    suggestion.value = ""
    message.success("已保存")
  } catch (error) {
    message.error(error instanceof Error ? error.message : "保存失败")
  } finally {
    saving.value = false
  }
}

async function expand() {
  if (!node.value) return
  const result = await api.expandOutline(node.value.id)
  form.content = result.content
  suggestion.value = "扩展建议已放进正文，保存后才会写入。"
}

async function toChapter() {
  if (!node.value) return
  if (node.value.chapter_id) {
    await router.push(`/write/${novelId.value}/${node.value.chapter_id}`)
    return
  }
  const result = await api.outlineToChapter(node.value.id)
  message.success("已生成章节")
  await router.push(`/write/${novelId.value}/${result.chapter_id}`)
}

watch(() => [novelId.value, nodeId.value], () => {
  const expand = route.query.expand === "1"
  if (expand) void router.replace({ path: route.path, query: {} })
  void load(expand).catch((error: unknown) => {
    message.error(error instanceof Error ? error.message : "加载失败")
  })
}, { immediate: true })
</script>

<template>
  <main class="page" v-if="node">
    <header class="workspace-head pin-head">
      <h1>编辑大纲</h1>
      <div class="actions">
        <NButton size="small" @click="router.push(`/novels/${novelId}/outline`)">返回大纲</NButton>
        <NButton size="small" type="primary" :loading="saving" @click="save">保存</NButton>
      </div>
    </header>
    <div class="outline-edit-grid">
      <section>
        <input v-model="form.title" class="outline-title" aria-label="大纲标题" />
        <textarea v-model="form.content" class="outline-body" placeholder="写这一段大纲" />
      </section>
      <aside class="panel pin-side">
        <NFormItem label="状态"><NSelect v-model:value="form.status" :options="outlineStatus" /></NFormItem>
        <NFormItem label="备注"><NInput v-model:value="form.notes" type="textarea" :autosize="{ minRows: 2, maxRows: 4 }" /></NFormItem>
        <NFormItem label="关联世界"><NSelect v-model:value="form.world_id" clearable :options="worldOptions" placeholder="本书正在使用的世界" /></NFormItem>
        <NFormItem label="关联角色"><NSelect v-model:value="form.character_ids" multiple :options="characterOptions" placeholder="本书正在使用的角色" /></NFormItem>
        <div class="actions">
          <NButton size="small" @click="expand">扩展建议</NButton>
          <NButton size="small" @click="toChapter">{{ node.chapter_id ? "打开章节" : "转为章节" }}</NButton>
        </div>
        <p v-if="suggestion" class="muted">{{ suggestion }}</p>
      </aside>
    </div>
  </main>
</template>
