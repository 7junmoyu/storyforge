import { createApp } from "vue"
import { createRouter, createWebHistory } from "vue-router"
import App from "./App.vue"
import EditorView from "./views/EditorView.vue"
import HomeView from "./views/HomeView.vue"
import LibraryView from "./views/LibraryView.vue"
import NovelSpaceView from "./views/NovelSpaceView.vue"
import OutlineEditorView from "./views/OutlineEditorView.vue"
import ResourceView from "./views/ResourceView.vue"
import WorkbenchView from "./views/WorkbenchView.vue"
import "./styles.css"

const router = createRouter({
  history: createWebHistory(),
  routes: [
    { path: "/", component: HomeView },
    { path: "/novels", component: WorkbenchView },
    { path: "/worlds", component: WorkbenchView },
    { path: "/worlds/:worldId/:section", component: ResourceView },
    { path: "/characters", component: LibraryView },
    { path: "/characters/:characterId/:section", component: ResourceView },
    { path: "/settings", component: LibraryView },
    { path: "/novels/:novelId/outline/:nodeId", component: OutlineEditorView },
    { path: "/novels/:novelId/:section", component: NovelSpaceView },
    { path: "/novels/:novelId", redirect: (to) => `/novels/${String(to.params.novelId)}/overview` },
    { path: "/write/:novelId/:chapterId", component: EditorView },
  ],
})

createApp(App).use(router).mount("#app")
