/** Minimal Markdown renderer ported from the prototype (safe: escapes HTML first). */

export function escapeHtml(s: string): string {
  return s.replace(/[&<>]/g, (c) => ({ '&': '&amp;', '<': '&lt;', '>': '&gt;' }[c] as string))
}

export function renderMarkdown(source: string): string {
  return source
    .split('```')
    .map((part, i) => {
      if (i % 2) {
        return '<pre><code>' + escapeHtml(part.replace(/^\w*\n/, '')) + '</code></pre>'
      }
      let html = ''
      let inList = false
      escapeHtml(part)
        .split('\n')
        .forEach((line) => {
          const match = line.match(/^\s*[-*] (.*)/) || line.match(/^\s*\d+[.、] (.*)/)
          if (match) {
            if (!inList) {
              html += '<ul>'
              inList = true
            }
            html += '<li>' + match[1] + '</li>'
          } else {
            if (inList) {
              html += '</ul>'
              inList = false
            }
            if (line.trim()) html += '<p>' + line + '</p>'
          }
        })
      if (inList) html += '</ul>'
      return html
        .replace(/`([^`]+)`/g, '<code>$1</code>')
        .replace(/\*\*([^*]+)\*\*/g, '<b>$1</b>')
    })
    .join('')
}

/** Deterministic hue per category id, matching the prototype palette. */
export function categoryHue(id: number): number {
  return (id * 53 + 235) % 360
}
