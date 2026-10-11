import { useCallback, useEffect, useState } from 'react'
import { api } from '../api/client'
import type { Card, Category } from '../api/types'
import { CategoryDot, Markdown } from '../components/Markdown'
import { useToast } from '../components/Toast'
import { categoryHue } from '../utils'
import { CardForm } from './CardForm'

interface Props {
  categories: Category[]
  onDataChanged: () => void
  initialCategoryId?: number | 'all'
}

const PAGE_SIZE = 20

export function CardsPage({ categories, onDataChanged, initialCategoryId = 'all' }: Props) {
  const { toast } = useToast()
  const [categoryFilter, setCategoryFilter] = useState<number | 'all'>(initialCategoryId)
  const [keywordInput, setKeywordInput] = useState('')
  const [keyword, setKeyword] = useState('')
  const [page, setPage] = useState(1)
  const [cards, setCards] = useState<Card[]>([])
  const [total, setTotal] = useState(0)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState('')
  const [expanded, setExpanded] = useState<Record<number, boolean>>({})
  const [flashId, setFlashId] = useState(0)
  const [editing, setEditing] = useState<Card | null>(null)
  const [creating, setCreating] = useState(false)

  const nameOf = useCallback(
    (id: number) => categories.find((c) => c.id === id)?.name ?? '未分类',
    [categories],
  )

  // Debounce the keyword box so typing doesn't hammer the API.
  useEffect(() => {
    const timer = window.setTimeout(() => {
      setKeyword(keywordInput)
      setPage(1)
    }, 300)
    return () => clearTimeout(timer)
  }, [keywordInput])

  const load = useCallback(async () => {
    setLoading(true)
    setError('')
    try {
      const data = await api.listCards({
        categoryId: categoryFilter,
        keyword,
        page,
        pageSize: PAGE_SIZE,
      })
      setTotal(data.total)
      // Deleting the last card on a page can leave it out of range; step back.
      const maxPage = Math.max(1, Math.ceil(data.total / PAGE_SIZE))
      if (page > maxPage) {
        setPage(maxPage)
        return
      }
      setCards(data.items)
    } catch (e) {
      setError(e instanceof Error ? e.message : '加载失败')
      setCards([])
      setTotal(0)
    } finally {
      setLoading(false)
    }
  }, [categoryFilter, keyword, page])

  useEffect(() => {
    void load()
  }, [load])

  const afterMutation = useCallback(
    async (message: string, cardId?: number) => {
      if (cardId) setFlashId(cardId)
      await load()
      onDataChanged()
      toast(message)
    },
    [load, onDataChanged, toast],
  )

  // One-click delete with an undo toast, matching the prototype's feel.
  const remove = async (card: Card) => {
    const snapshot = { ...card }
    try {
      await api.deleteCard(card.id)
      await load()
      onDataChanged()
      toast('已删除', () => {
        void (async () => {
          try {
            await api.restoreCard({
              id: snapshot.id,
              question: snapshot.question,
              answer: snapshot.answer,
              category_id: snapshot.category_id,
              review_count: snapshot.review_count,
            })
            await load()
            onDataChanged()
            setFlashId(snapshot.id)
            toast('已撤销')
          } catch {
            toast('撤销失败')
          }
        })()
      })
    } catch (e) {
      toast(e instanceof Error ? e.message : '删除失败')
    }
  }

  const totalPages = Math.max(1, Math.ceil(total / PAGE_SIZE))
  const showEmpty = !loading && !error && cards.length === 0
  const isFiltering = Boolean(keyword) || categoryFilter !== 'all'

  return (
    <div className="view">
      <h1>卡片</h1>

      <div className="tool">
        <input
          placeholder="搜索题目"
          value={keywordInput}
          onChange={(e) => setKeywordInput(e.target.value)}
        />
        <select
          value={categoryFilter}
          onChange={(e) => {
            const v = e.target.value
            setCategoryFilter(v === 'all' ? 'all' : Number(v))
            setPage(1)
          }}
        >
          <option value="all">全部分类</option>
          {categories.map((c) => (
            <option key={c.id} value={c.id}>
              {c.name}（{c.card_count}）
            </option>
          ))}
        </select>
        <button className="btn pri" onClick={() => setCreating(true)}>
          新增卡片
        </button>
      </div>

      {!loading && !error && <p className="card-total">共 {total} 张</p>}

      {loading && (
        <>
          <div className="skeleton" />
          <div className="skeleton" />
          <div className="skeleton" />
        </>
      )}

      {error && (
        <div className="empty">
          <p>{error}</p>
          <button className="btn pri" onClick={() => void load()}>
            重试
          </button>
        </div>
      )}

      {showEmpty && (
        <div className="empty">
          <p>{isFiltering ? '没有找到匹配的卡片' : '还没有卡片'}</p>
          <button className="btn pri" onClick={() => setCreating(true)}>
            新增卡片
          </button>
        </div>
      )}

      {cards.map((card) => (
        <div
          key={card.id}
          className={`row ${expanded[card.id] ? 'open' : ''} ${
            flashId === card.id ? 'flash' : ''
          }`}
          style={{ ['--h' as string]: categoryHue(card.category_id) }}
          onAnimationEnd={() => setFlashId(0)}
        >
          <div
            className="rh"
            onClick={() => setExpanded((prev) => ({ ...prev, [card.id]: !prev[card.id] }))}
          >
            <CategoryDot hue={categoryHue(card.category_id)} />
            <span className="rq">{card.question}</span>
            <span className="meta">
              {nameOf(card.category_id)}　复习 {card.review_count} 次
            </span>
            <span className="acts">
              <button
                className="btn sm"
                onClick={(e) => {
                  e.stopPropagation()
                  setEditing(card)
                }}
              >
                编辑
              </button>
              <button
                className="btn sm del"
                onClick={(e) => {
                  e.stopPropagation()
                  void remove(card)
                }}
              >
                删除
              </button>
            </span>
          </div>
          <div className="rb">
            <div>
              <div className="md">
                <Markdown source={card.answer} />
              </div>
            </div>
          </div>
        </div>
      ))}

      {!loading && !error && totalPages > 1 && (
        <div className="page">
          <button
            className="btn sm"
            disabled={page <= 1}
            onClick={() => setPage((p) => Math.max(1, p - 1))}
          >
            上一页
          </button>
          <span>
            第 {page} / {totalPages} 页
          </span>
          <button
            className="btn sm"
            disabled={page >= totalPages}
            onClick={() => setPage((p) => Math.min(totalPages, p + 1))}
          >
            下一页
          </button>
        </div>
      )}

      {creating && (
        <CardForm
          categories={categories}
          defaultCategoryId={categoryFilter === 'all' ? undefined : categoryFilter}
          onClose={() => setCreating(false)}
          onSaved={() => void afterMutation('已添加')}
        />
      )}

      {editing && (
        <CardForm
          categories={categories}
          card={editing}
          onClose={() => setEditing(null)}
          onSaved={() => void afterMutation('已保存', editing.id)}
        />
      )}
    </div>
  )
}
