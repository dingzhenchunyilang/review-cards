import { useCallback, useEffect, useState } from 'react'
import type { ReactElement } from 'react'
import { api } from './api/client'
import type { Category } from './api/types'
import { ToastProvider } from './components/Toast'
import { CategoriesPage } from './pages/CategoriesPage'
import { CardsPage } from './pages/CardsPage'
import { ReviewPage } from './pages/ReviewPage'

type Tab = 'review' | 'cards' | 'cats'
const TABS: Tab[] = ['review', 'cards', 'cats']
const TAB_LABELS: Record<Tab, string> = { review: '复习', cards: '卡片', cats: '分类' }

// Inline icons straight from the prototype.
const TAB_ICONS: Record<Tab, ReactElement> = {
  review: (
    <svg viewBox="0 0 24 24">
      <rect x="3.5" y="7" width="17" height="12" rx="3" />
      <path d="M7 3.5h10" />
    </svg>
  ),
  cards: (
    <svg viewBox="0 0 24 24">
      <path d="M9 6h11M9 12h11M9 18h11M4.5 6h.01M4.5 12h.01M4.5 18h.01" />
    </svg>
  ),
  cats: (
    <svg viewBox="0 0 24 24">
      <rect x="4" y="4" width="6.5" height="6.5" rx="2" />
      <rect x="13.5" y="4" width="6.5" height="6.5" rx="2" />
      <rect x="4" y="13.5" width="6.5" height="6.5" rx="2" />
      <rect x="13.5" y="13.5" width="6.5" height="6.5" rx="2" />
    </svg>
  ),
}

function useTheme() {
  const [theme, setTheme] = useState<'light' | 'dark'>(() =>
    window.matchMedia('(prefers-color-scheme: dark)').matches ? 'dark' : 'light',
  )

  useEffect(() => {
    const root = document.documentElement
    // 'light' is written explicitly so it wins over prefers-color-scheme.
    root.dataset.theme = theme
  }, [theme])

  const toggle = useCallback(
    () => setTheme((t) => (t === 'dark' ? 'light' : 'dark')),
    [],
  )
  return { theme, toggle }
}

export default function App() {
  const [tab, setTab] = useState<Tab>('review')
  const [categories, setCategories] = useState<Category[]>([])
  const [cardsFilter, setCardsFilter] = useState<number | 'all'>('all')
  const { theme, toggle } = useTheme()

  const loadCategories = useCallback(async () => {
    try {
      setCategories(await api.listCategories())
    } catch {
      setCategories([])
    }
  }, [])

  useEffect(() => {
    void loadCategories()
  }, [loadCategories])

  const goToCards = useCallback(
    (categoryId: number | 'all' = 'all') => {
      setCardsFilter(categoryId)
      setTab('cards')
    },
    [],
  )

  return (
    <ToastProvider>
      <div className="app">
        <aside className="side">
          <div className="logo">
            <i />
            知识卡片
          </div>
          <nav className="nav">
            <i className="ind" style={{ ['--i' as string]: TABS.indexOf(tab) }} />
            {TABS.map((t) => (
              <button key={t} className={tab === t ? 'on' : ''} onClick={() => setTab(t)}>
                {TAB_ICONS[t]}
                {TAB_LABELS[t]}
              </button>
            ))}
          </nav>
          <button className="theme" onClick={toggle}>
            {theme === 'dark' ? '切换浅色' : '切换深色'}
          </button>
        </aside>

        <main>
          {tab === 'review' && (
            <ReviewPage
              categories={categories}
              onDataChanged={loadCategories}
              onGoCards={() => goToCards()}
            />
          )}
          {tab === 'cards' && (
            <CardsPage
              categories={categories}
              onDataChanged={loadCategories}
              initialCategoryId={cardsFilter}
            />
          )}
          {tab === 'cats' && (
            <CategoriesPage categories={categories} onDataChanged={loadCategories} />
          )}
        </main>
      </div>
    </ToastProvider>
  )
}
