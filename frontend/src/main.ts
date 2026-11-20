import { createApp } from "vue"
import { createRouter, createWebHistory } from "vue-router"
import App from "./App.vue"
import EditorView from "./views/EditorView.vue"
import WorkbenchView from "./views/WorkbenchView.vue"
import "./styles.css"

const router = createRouter({
  history: createWebHistory(),
  routes: [
    { path: "/", component: WorkbenchView },
    { path: "/novels/:id", component: EditorView },
  ],
})

createApp(App).use(router).mount("#app")
