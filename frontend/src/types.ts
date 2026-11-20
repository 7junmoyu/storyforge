export type World = {
  id: string
  name: string
  summary: string
  novel_count: number
  created_at: string
  updated_at: string
}

export type WorldBrief = {
  id: string
  name: string
}

export type Novel = {
  id: string
  title: string
  summary: string
  genre: string
  status: "draft" | "writing" | "finished"
  target_words: number
  word_count: number
  chapter_count: number
  worlds: WorldBrief[]
  created_at: string
  updated_at: string
}

export type ChapterBrief = {
  id: string
  title: string
  position: number
  word_count: number
  updated_at: string
}

export type NovelDetail = Novel & {
  chapters: ChapterBrief[]
}

export type Chapter = {
  id: string
  novel_id: string
  title: string
  content: string
  position: number
  word_count: number
  updated_at: string
}

export type Revision = {
  id: string
  word_count: number
  created_at: string
}

export type AiAction = "continue" | "expand" | "polish" | "rewrite"

export type Suggestion = {
  id: string
  action: AiAction
  source_text: string
  suggestion: string
  status: "pending" | "accepted" | "rejected"
  provider: "demo" | "model"
  created_at: string
}
