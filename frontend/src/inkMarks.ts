import { Extension } from "@tiptap/core"
import { Plugin, PluginKey } from "@tiptap/pm/state"
import { Decoration, DecorationSet } from "@tiptap/pm/view"

export const inkMarkKey = new PluginKey("inkMarks")

export type InkRange = { start: number; end: number }

export const InkMarks = Extension.create({
  name: "inkMarks",
  addProseMirrorPlugins() {
    return [
      new Plugin({
        key: inkMarkKey,
        state: {
          init: () => DecorationSet.empty,
          apply(tr, old) {
            const next = tr.getMeta(inkMarkKey) as InkRange[] | undefined
            if (!next) return old.map(tr.mapping, tr.doc)
            const decos = next.flatMap((item) => {
              if (item.start < 0 || item.end > tr.doc.content.size || item.start >= item.end) return []
              try {
                tr.doc.resolve(item.start)
                tr.doc.resolve(item.end)
                return [Decoration.inline(item.start, item.end, { class: "ink-mark" })]
              } catch {
                return []
              }
            })
            return DecorationSet.create(tr.doc, decos)
          },
        },
        props: {
          decorations(state) {
            return inkMarkKey.getState(state)
          },
        },
      }),
    ]
  },
})
