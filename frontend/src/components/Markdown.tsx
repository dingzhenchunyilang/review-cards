import { renderMarkdown } from '../utils'

export function Markdown({ source }: { source: string }) {
  return <div className="md" dangerouslySetInnerHTML={{ __html: renderMarkdown(source) }} />
}

export function CategoryTag({ name, hue }: { name: string; hue: number }) {
  return (
    <span className="tag" style={{ ['--h' as string]: hue }}>
      {name}
    </span>
  )
}

export function CategoryDot({ hue }: { hue: number }) {
  return <span className="dot" style={{ ['--h' as string]: hue }} />
}
