import type {
  AiAction,
  Chapter,
  Character,
  Foreshadow,
  Novel,
  PendingSuggestion,
  NovelDetail,
  OutlineDraftNode,
  OutlineNode,
  Revision,
  Volume,
  Suggestion,
  World,
} from "./types"

async function request<T>(path: string, init?: RequestInit): Promise<T> {
  const response = await fetch(path, {
    ...init,
    headers: {
      "Content-Type": "application/json",
      ...(init?.headers ?? {}),
    },
  })
  if (!response.ok) {
    let detail = "请求失败"
    try {
      const body = (await response.json()) as { detail?: unknown }
      if (typeof body.detail === "string") detail = body.detail
    } catch {
      detail = response.statusText || detail
    }
    throw new Error(detail)
  }
  if (response.status === 204) return undefined as T
  return (await response.json()) as T
}

export const api = {
  worlds: () => request<World[]>("/api/worlds"),
  createWorld: (body: { name: string; summary: string }) =>
    request<World>("/api/worlds", { method: "POST", body: JSON.stringify(body) }),
  updateWorld: (id: string, body: { name: string; summary: string }) =>
    request<World>(`/api/worlds/${id}`, { method: "PATCH", body: JSON.stringify(body) }),
  deleteWorld: (id: string) => request<void>(`/api/worlds/${id}`, { method: "DELETE" }),
  worldRelations: (id: string) =>
    request<{ id: string; name: string; summary: string; novels: { id: string; title: string }[]; characters: { id: string; name: string; note: string }[] }>(
      `/api/worlds/${id}/relations`,
    ),
  characterWorlds: (id: string) => request<{ id: string; name: string; summary: string; note: string }[]>(`/api/characters/${id}/worlds`),
  linkCharacterWorld: (characterId: string, body: { world_id: string; note: string }) =>
    request<{ id: string; name: string; note: string }>(`/api/characters/${characterId}/worlds`, { method: "POST", body: JSON.stringify(body) }),
  unlinkCharacterWorld: (characterId: string, worldId: string) =>
    request<void>(`/api/characters/${characterId}/worlds/${worldId}`, { method: "DELETE" }),
  marks: (chapterId: string) => request<{ id: string; quote: string; start: number; end: number; chapter_id: string }[]>(`/api/chapters/${chapterId}/marks`),
  createMark: (chapterId: string, body: { quote: string; start: number; end: number }) =>
    request<{ id: string; quote: string; start: number; end: number }>(`/api/chapters/${chapterId}/marks`, { method: "POST", body: JSON.stringify(body) }),
  deleteMark: (id: string) => request<void>(`/api/marks/${id}`, { method: "DELETE" }),
  novels: (includeArchived = false) => request<Novel[]>(`/api/novels?include_archived=${includeArchived ? "true" : "false"}`),
  characters: (q = "") => request<Character[]>(`/api/characters?q=${encodeURIComponent(q)}`),
  createCharacter: (body: { name: string; summary: string }) =>
    request<Character>("/api/characters", { method: "POST", body: JSON.stringify(body) }),
  updateCharacter: (id: string, body: { name: string; summary: string }) =>
    request<Character>(`/api/characters/${id}`, { method: "PATCH", body: JSON.stringify(body) }),
  deleteCharacter: (id: string) => request<void>(`/api/characters/${id}`, { method: "DELETE" }),
  novel: (id: string) => request<NovelDetail>(`/api/novels/${id}`),
  createNovel: (body: {
    title: string
    summary: string
    genre: string
    status: Novel["status"]
    target_words: number
    world_id?: string | null
    world_ids?: string[]
    character_ids?: string[]
    tags?: string
    cover_url?: string
  }) => request<NovelDetail>("/api/novels", { method: "POST", body: JSON.stringify(body) }),
  duplicateNovel: (id: string) => request<NovelDetail>(`/api/novels/${id}/duplicate`, { method: "POST" }),
  importNovel: (body: Record<string, unknown>) =>
    request<NovelDetail>("/api/novels/import", { method: "POST", body: JSON.stringify(body) }),
  volumes: (novelId: string) => request<Volume[]>(`/api/novels/${novelId}/volumes`),
  createVolume: (novelId: string, title: string) =>
    request<Volume>(`/api/novels/${novelId}/volumes`, { method: "POST", body: JSON.stringify({ title }) }),
  deleteVolume: (novelId: string, volumeId: string) =>
    request<void>(`/api/novels/${novelId}/volumes/${volumeId}`, { method: "DELETE" }),
  updateNovel: (id: string, body: Record<string, unknown>) =>
    request<Novel>(`/api/novels/${id}`, { method: "PATCH", body: JSON.stringify(body) }),
  deleteNovel: (id: string) => request<void>(`/api/novels/${id}`, { method: "DELETE" }),
  createChapter: (novelId: string, title: string) =>
    request<Chapter>(`/api/novels/${novelId}/chapters`, { method: "POST", body: JSON.stringify({ title }) }),
  chapter: (id: string) => request<Chapter>(`/api/chapters/${id}`),
  updateChapter: (id: string, body: { title?: string; content?: string; volume_id?: string | null; clear_volume?: boolean }) =>
    request<Chapter>(`/api/chapters/${id}`, { method: "PATCH", body: JSON.stringify(body) }),
  deleteChapter: (id: string) => request<void>(`/api/chapters/${id}`, { method: "DELETE" }),
  revisions: (id: string) => request<Revision[]>(`/api/chapters/${id}/revisions`),
  restoreRevision: (chapterId: string, revisionId: string) =>
    request<Chapter>(`/api/chapters/${chapterId}/revisions/${revisionId}/restore`, { method: "POST" }),
  suggest: (chapterId: string, action: AiAction, selectedText: string) =>
    request<Suggestion>(`/api/chapters/${chapterId}/suggestions`, {
      method: "POST",
      body: JSON.stringify({ action, selected_text: selectedText }),
    }),
  acceptSuggestion: (id: string) => request<Suggestion>(`/api/suggestions/${id}/accept`, { method: "POST" }),
  rejectSuggestion: (id: string) => request<Suggestion>(`/api/suggestions/${id}/reject`, { method: "POST" }),
  moveChapter: (id: string, direction: "up" | "down") =>
    request<Chapter[]>(`/api/chapters/${id}/move`, { method: "POST", body: JSON.stringify({ direction }) }),
  outline: (novelId: string) => request<OutlineNode[]>(`/api/novels/${novelId}/outline`),
  createOutline: (novelId: string, body: Record<string, unknown>) =>
    request<OutlineNode>(`/api/novels/${novelId}/outline`, { method: "POST", body: JSON.stringify(body) }),
  updateOutline: (id: string, body: Record<string, unknown>) =>
    request<OutlineNode>(`/api/outline-nodes/${id}`, { method: "PATCH", body: JSON.stringify(body) }),
  deleteOutline: (id: string) => request<void>(`/api/outline-nodes/${id}`, { method: "DELETE" }),
  moveOutline: (id: string, direction: "up" | "down") =>
    request<OutlineNode[]>(`/api/outline-nodes/${id}/move`, { method: "POST", body: JSON.stringify({ direction }) }),
  reorderOutline: (novelId: string, items: { id: string; parent_id: string | null; position: number }[]) =>
    request<OutlineNode[]>(`/api/novels/${novelId}/outline/reorder`, { method: "POST", body: JSON.stringify(items) }),
  outlineToChapter: (id: string) =>
    request<{ chapter_id: string }>(`/api/outline-nodes/${id}/to-chapter`, { method: "POST" }),
  expandOutline: (id: string) =>
    request<{ provider: string; content: string }>(`/api/outline-nodes/${id}/draft-expand`, { method: "POST" }),
  checkOutline: (novelId: string) =>
    request<{ provider: string; report: string }>(`/api/novels/${novelId}/outline/check`, { method: "POST" }),
  reviewForeshadows: (novelId: string, kind = "forgotten") =>
    request<{ provider: string; report: string; findings: { foreshadow_id: string; name: string; reason: string; proposed_status: string | null }[] }>(
      `/api/novels/${novelId}/foreshadows/review?kind=${kind}`,
      { method: "POST" },
    ),
  pendingSuggestions: () => request<PendingSuggestion[]>("/api/inbox/suggestions"),
  draftOutline: (novelId: string, instruction: string) =>
    request<{ provider: string; nodes: OutlineDraftNode[] }>(`/api/novels/${novelId}/outline/draft`, {
      method: "POST",
      body: JSON.stringify({ instruction }),
    }),
  foreshadows: (novelId: string, query = "") => request<Foreshadow[]>(`/api/novels/${novelId}/foreshadows${query}`),
  createForeshadow: (novelId: string, body: Record<string, unknown>) =>
    request<Foreshadow>(`/api/novels/${novelId}/foreshadows`, { method: "POST", body: JSON.stringify(body) }),
  updateForeshadow: (id: string, body: Record<string, unknown>) =>
    request<Foreshadow>(`/api/foreshadows/${id}`, { method: "PATCH", body: JSON.stringify(body) }),
  deleteForeshadow: (id: string) => request<void>(`/api/foreshadows/${id}`, { method: "DELETE" }),
  foreshadowInbox: () => request<Foreshadow[]>("/api/inbox/foreshadows"),
  draftForeshadow: (novelId: string, instruction: string) =>
    request<{ provider: string; suggestion: Partial<Foreshadow> }>(`/api/novels/${novelId}/foreshadows/draft`, {
      method: "POST",
      body: JSON.stringify({ instruction }),
    }),
  settings: () => request<{ ai_configured: boolean; ai_model: string; ai_base_url: string }>("/api/settings"),
}
