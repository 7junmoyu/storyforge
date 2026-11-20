<script setup lang="ts">
import { darkTheme, lightTheme, NButton, NConfigProvider, NDialogProvider, NMessageProvider } from "naive-ui"
import { computed, ref } from "vue"
import { RouterLink, RouterView } from "vue-router"

const themeName = ref(localStorage.getItem("sf-theme") === "light" ? "light" : "dark")
document.documentElement.dataset.theme = themeName.value

const theme = computed(() => (themeName.value === "dark" ? darkTheme : lightTheme))
const overrides = computed(() => ({
  common: {
    primaryColor: themeName.value === "dark" ? "#c6a36a" : "#8d6430",
    primaryColorHover: themeName.value === "dark" ? "#d7b888" : "#a47a3f",
    primaryColorPressed: themeName.value === "dark" ? "#a6844e" : "#6f4e24",
    primaryColorSuppl: themeName.value === "dark" ? "#c6a36a" : "#8d6430",
    borderRadius: "10px",
  },
}))

function toggleTheme() {
  themeName.value = themeName.value === "dark" ? "light" : "dark"
  localStorage.setItem("sf-theme", themeName.value)
  document.documentElement.dataset.theme = themeName.value
}
</script>

<template>
  <NConfigProvider :theme="theme" :theme-overrides="overrides">
    <NMessageProvider>
      <NDialogProvider>
        <div class="shell">
          <header class="topbar">
            <RouterLink class="brand" to="/">
              <strong>StoryForge</strong>
              <span>写作台</span>
            </RouterLink>
            <NButton quaternary @click="toggleTheme">{{ themeName === "dark" ? "浅色" : "深色" }}</NButton>
          </header>
          <RouterView />
        </div>
      </NDialogProvider>
    </NMessageProvider>
  </NConfigProvider>
</template>
