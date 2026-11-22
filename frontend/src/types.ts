export type World = {
  id: string
  name: string
  summary: string
  cover_url: string
  novel_count: number
  created_at: string
  updated_at: string
}

export type WorldBrief = {
  id: string
  name: string
}

export type ResourceLink = {
  id: string
  name: string
  summary?: string
  note: string
  scope: "global" | "novel"
  source: string
  novel_id: string | null
  novel_title: string
  created_at: string
}

export type Character = {
  id: string
  name: string
  summary: string
  cover_url: string
  attributes: Record<string, string>
  novel_count: number
  created_at: string
  updated_at: string
}

export type WorldRecord = {
  id: string
  world_id: string
  kind: "object" | "faction" | "place" | "event"
  name: string
  summary: string
  time_label: string
  updated_at: string
}

export type AttributeTemplate = {
  id: string
  name: string
  target: string
  fields: string[]
}

export type MediaAsset = {
  id: string
  owner_kind: string
  owner_id: string | null
  filename: string
  mime: string
  note: string
  url: string
  created_at: string
}

export type CharacterPeriod = {
  id: string
  character_id: string
  name: string
  time_range: string
  attributes: Record<string, string>
  position: number
  updated_at: string
}

export type CharacterVersion = {
  id: string
  novel_id: string
  novel_title: string
  character_id: string
  period_id: string | null
  name: string
  summary: string
  attributes: Record<string, string>
  updated_at: string
}

export type Novel = {
  id: string
  title: string
  summary: string
  genre: string
  status: "draft" | "writing" | "finished"
  target_words: number
  tags: string
  cover_url: string
  archived: boolean
  word_count: number
  chapter_count: number
  worlds: WorldBrief[]
  characters: WorldBrief[]
  group_id: string | null
  grouped_at: string | null
  created_at: string
  updated_at: string
}

export type NovelGroup = {
  id: string
  name: string
  created_at: string
  updated_at: string
}

export type ChapterBrief = {
  id: string
  title: string
  position: number
  word_count: number
  volume_id: string | null
  world_id: string | null
  excerpt?: string
  updated_at: string
}

export type Volume = {
  id: string
  novel_id: string
  title: string
  position: number
}

export type NovelDetail = Novel & {
  chapters: ChapterBrief[]
}

export type Chapter = {
  id: string
  novel_id: string
  volume_id: string | null
  world_id: string | null
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

export type AiAction = "continue" | "expand" | "polish" | "rewrite" | "shorten" | "style" | "dialogue" | "character" | "plot" | "conflict"

export type OutlineNode = {
  id: string
  novel_id: string
  parent_id: string | null
  chapter_id: string | null
  world_id: string | null
  title: string
  content: string
  notes: string
  status: "pending" | "active" | "done"
  position: number
  character_ids: string[]
  updated_at: string
}

export type OutlineDraftNode = {
  title: string
  content: string
  children: OutlineDraftNode[]
}

export type Foreshadow = {
  id: string
  novel_id: string
  novel_title?: string
  outline_node_id: string | null
  name: string
  content: string
  kind: string
  importance: "low" | "medium" | "high"
  status: "planned" | "planted" | "pending_payoff" | "paid" | "discarded"
  plant_chapter_id: string | null
  expected_chapter_id: string | null
  actual_chapter_id: string | null
  source_quote: string
  source_start: number | null
  source_end: number | null
  notes: string
  character_ids: string[]
  updated_at: string
}

export type PendingSuggestion = {
  id: string
  action: string
  chapter_id: string
  chapter_title: string
  novel_id: string
  novel_title: string
  created_at: string
}

export type Suggestion = {
  id: string
  action: AiAction
  source_text: string
  suggestion: string
  status: "pending" | "accepted" | "rejected"
  provider: "demo" | "model"
  created_at: string
}
