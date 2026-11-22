<script setup lang="ts">
import { ref } from "vue"
import { useMessage } from "naive-ui"
import { api } from "../api"
import type { CoverChoice } from "../covers"
import CoverCrop from "./CoverCrop.vue"

const props = defineProps<{
  modelValue: string
  choices: CoverChoice[]
  ownerKind: string
  ownerId?: string
}>()
const emit = defineEmits<{ "update:modelValue": [value: string] }>()
const message = useMessage()
const input = ref<HTMLInputElement | null>(null)
const cropFile = ref<File | null>(null)

function choose(url: string) {
  cropFile.value = null
  emit("update:modelValue", url)
}

function onFile(event: Event) {
  const element = event.target as HTMLInputElement
  const file = element.files?.[0]
  element.value = ""
  if (file) cropFile.value = file
}

async function useCrop(file: File) {
  try {
    const asset = await api.uploadAsset(file, props.ownerKind, props.ownerId || "")
    emit("update:modelValue", asset.url)
    cropFile.value = null
    message.success("图片已截取")
  } catch (error) {
    message.error(error instanceof Error ? error.message : "上传失败")
  }
}
</script>

<template>
  <div>
    <div class="cover-choices">
      <button v-for="cover in choices" :key="cover.url" type="button" :class="{ on: modelValue === cover.url }" @click="choose(cover.url)">
        <img :src="cover.url" :alt="cover.name" />
      </button>
      <img v-if="modelValue && !choices.some((cover) => cover.url === modelValue)" class="book-cover" :src="modelValue" alt="当前图片" />
    </div>
    <div class="actions" style="margin-top: 12px">
      <button class="quiet-button" type="button" @click="input?.click()">选择文件</button>
      <input ref="input" type="file" accept="image/jpeg,image/png,image/gif,image/webp" hidden @change="onFile" />
    </div>
    <CoverCrop v-if="cropFile" :file="cropFile" @use="useCrop" @cancel="cropFile = null" />
  </div>
</template>
