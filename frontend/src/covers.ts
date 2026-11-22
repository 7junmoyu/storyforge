export type CoverChoice = { name: string; url: string }

export const novelCovers: CoverChoice[] = [
  { name: "雾港", url: "/covers/default-harbor.png" },
  { name: "夜墨", url: "/covers/default-ink.png" },
  { name: "素纸", url: "/covers/default-paper.png" },
]

export const worldCovers: CoverChoice[] = [
  { name: "海岸", url: "/covers/world-coast.png" },
  { name: "山脊", url: "/covers/world-ridge.png" },
  { name: "星图", url: "/covers/world-stars.png" },
]

export const characterCovers: CoverChoice[] = [
  { name: "暖影", url: "/covers/character-warm.png" },
  { name: "青衫", url: "/covers/character-cool.png" },
  { name: "墨像", url: "/covers/character-ink.png" },
]

export const coverChoices = novelCovers

const fallbacks = {
  novel: novelCovers[0].url,
  world: worldCovers[0].url,
  character: characterCovers[0].url,
}

export const fallbackCover = fallbacks.novel

export function coverSrc(url: string, kind: keyof typeof fallbacks = "novel") {
  return url || fallbacks[kind]
}
