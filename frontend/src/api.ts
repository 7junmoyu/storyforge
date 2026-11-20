import type { AiAction, Chapter, Novel, NovelDetail, Revision, Suggestion, World } from "./types"

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
  novels: () => request<Novel[]>("/api/novels"),
  novel: (id: string) => request<NovelDetail>(`/api/novels/${id}`),
  createNovel: (body: {
    title: string
    summary: string
    genre: string
    status: Novel["status"]
    target_words: number
    world_id: string | null
  }) => request<NovelDetail>("/api/novels", { method: "POST", body: JSON.stringify(body) }),
  updateNovel: (id: string, body: Record<string, unknown>) =>
    request<Novel>(`/api/novels/${id}`, { method: "PATCH", body: JSON.stringify(body) }),
  deleteNovel: (id: string) => request<void>(`/api/novels/${id}`, { method: "DELETE" }),
  createChapter: (novelId: string, title: string) =>
    request<Chapter>(`/api/novels/${novelId}/chapters`, { method: "POST", body: JSON.stringify({ title }) }),
  chapter: (id: string) => request<Chapter>(`/api/chapters/${id}`),
  updateChapter: (id: string, body: { title?: string; content?: string }) =>
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
}
