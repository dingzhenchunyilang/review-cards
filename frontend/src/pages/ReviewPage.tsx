import { useCallback, useEffect, useRef, useState } from 'react'
import type { MouseEvent as ReactMouseEvent } from 'react'
import { flushSync } from 'react-dom'
import { api } from '../api/client'
import type { Card, Category } from '../api/types'
import { DEFAULT_CATEGORY_ID } from '../api/types'
import { CategoryTag, Markdown } from '../components/Markdown'
import { useToast } from '../components/Toast'
import { categoryHue } from '../utils'
import { CardForm } from './CardForm'

interface Props {
  categories: Category[]
  onDataChanged: () => void
  onGoCards: () => void
}

type Pool = number | 'all'

export function ReviewPage({ categories, onDataChanged, onGoCards }: Props) {
  const { toast } = useToast()
  const [pool, setPool] = useState<Pool>('all')
  const [card, setCard] = useState<Card | null>(null)
  const [flipped, setFlipped] = useState(false)
  const [seen, setSeen] = useState(0)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState('')
  const [editing, setEditing] = useState(false)
  const animating = useRef(false)
  const cardRef = useRef<HTMLDivElement>(null)
  const stageRef = useRef<HTMLDivElement>(null)
  const countRef = useRef<HTMLElement>(null)
  const canTilt = useRef(false)

  // Mouse parallax only when the device has a real pointer and motion is welcome.
  useEffect(() => {
    canTilt.current =
      !window.matchMedia('(prefers-reduced-motion: reduce)').matches &&
      window.matchMedia('(hover: hover)').matches
  }, [])

  const onTiltMove = (e: ReactMouseEvent<HTMLDivElement>) => {
    if (!canTilt.current || !stageRef.current) return
    const rect = e.currentTarget.getBoundingClientRect()
    const x = (e.clientX - rect.left) / rect.width - 0.5
    const y = (e.clientY - rect.top) / rect.height - 0.5
    stageRef.current.style.transform = `rotateY(${x * 7}deg) rotateX(${-y * 7}deg)`
  }

  const onTiltLeave = () => {
    if (stageRef.current) stageRef.current.style.transform = ''
  }

  const nameOf = useCallback(
    (id: number) => categories.find((c) => c.id === id)?.name ?? '未分类',
    [categories],
  )

  const fetchCard = useCallback(async (target: Pool, excludeId?: number) => {
    let next = await api.randomCard(target)
    // Avoid showing the same card twice in a row when alternatives exist.
    if (next && excludeId !== undefined && next.id === excludeId) {
      const retry = await api.randomCard(target)
      if (retry) next = retry
    }
    return next
  }, [])

  const loadCard = useCallback(
    async (target: Pool, excludeId?: number) => {
      setLoading(true)
      setError('')
      try {
        const next = await fetchCard(target, excludeId)
        setCard(next)
        setFlipped(false)
      } catch (e) {
        setError(e instanceof Error ? e.message : '加载失败')
        setCard(null)
      } finally {
        setLoading(false)
      }
    },
    [fetchCard],
  )

  useEffect(() => {
    void loadCard(pool)
  }, [pool, loadCard])

  const flip = useCallback(() => {
    if (!card) return
    setFlipped((f) => !f)
  }, [card])

  /**
   * Ported 1:1 from the prototype's next():
   *   counter pops -> old card flies out left -> flip snapped back with no transition
   *   -> content swapped -> new card slides in from the right.
   * The card must stay mounted the whole time, otherwise the exit animation gets
   * truncated, so this deliberately does NOT go through loadCard (which sets loading).
   */
  const next = useCallback(async () => {
    if (!card || animating.current) return
    animating.current = true

    const el = cardRef.current
    const flipper = el?.querySelector<HTMLElement>('.flipper') ?? null
    const finishedId = card.id
    const rm = window.matchMedia('(prefers-reduced-motion: reduce)').matches

    if (!rm && countRef.current) {
      countRef.current.animate([{ transform: 'scale(1.5)' }, { transform: 'none' }], 250)
    }

    const flyOut =
      !rm && el
        ? el
            .animate(
              [
                { transform: 'none', opacity: 1 },
                { transform: 'translateX(-55%) rotate(-7deg)', opacity: 0 },
              ],
              { duration: 280, easing: 'cubic-bezier(.5,0,.8,.4)', fill: 'forwards' },
            )
            .finished.catch(() => {})
        : Promise.resolve()

    setSeen((s) => s + 1)
    void api.markReviewed(finishedId).catch(() => {})

    let nextCard: Card | null = null
    try {
      const [fetched] = await Promise.all([fetchCard(pool, finishedId), flyOut])
      nextCard = fetched
    } catch (e) {
      if (el) el.getAnimations().forEach((a) => a.cancel())
      if (flipper) flipper.style.transition = ''
      setError(e instanceof Error ? e.message : '加载失败')
      animating.current = false
      return
    }

    // Drop the forwards-fill, then disable the flip transition so the card snaps
    // back to its front face instantly instead of rotating 0.8s with new content.
    if (el) {
      el.getAnimations().forEach((a) => a.cancel())
      if (flipper) flipper.style.transition = 'none'
    }

    // One synchronous commit: new text and un-flipped land in the same paint.
    flushSync(() => {
      setCard(nextCard)
      setFlipped(false)
    })

    if (flipper) {
      void flipper.offsetWidth
      flipper.style.transition = ''
    }

    if (!rm && el) {
      el.animate(
        [
          { transform: 'translateX(30%) scale(.96)', opacity: 0 },
          { transform: 'none', opacity: 1 },
        ],
        { duration: 420, easing: 'cubic-bezier(.2,.9,.3,1)' },
      )
    }
    animating.current = false
  }, [card, pool, fetchCard])

  useEffect(() => {
    const onKey = (e: KeyboardEvent) => {
      const tag = (document.activeElement?.tagName ?? '').toUpperCase()
      if (document.querySelector('.ov')) return
      if (['INPUT', 'TEXTAREA', 'SELECT'].includes(tag)) return
      if (e.key === ' ') {
        e.preventDefault()
        flip()
      } else if (e.key === 'ArrowRight' || e.key === 'Enter') {
        e.preventDefault()
        void next()
      } else if ((e.key === 'e' || e.key === 'E') && card) {
        setEditing(true)
      }
    }
    window.addEventListener('keydown', onKey)
    return () => window.removeEventListener('keydown', onKey)
  }, [flip, next, card])

  const poolCards = pool === 'all' ? null : categories.find((c) => c.id === pool)
  const poolCount = pool === 'all' ? undefined : poolCards?.card_count
  const empty = !loading && !error && !card

  // The prototype hides 未分类 while it is empty — there is nothing to review in
  // it. It stays visible if it is the current pool so the row keeps an active
  // pill when the last card is moved out.
  const visibleCategories = categories.filter(
    (c) => c.id !== DEFAULT_CATEGORY_ID || c.card_count > 0 || c.id === pool,
  )

  return (
    <div className="view">
      <div className="bar">
        <div className="pills">
          <button
            className={`pill ${pool === 'all' ? 'on' : ''}`}
            onClick={() => {
              setPool('all')
              setSeen(0)
            }}
          >
            全部
            <i>
              {categories.reduce((sum, c) => sum + c.card_count, 0)}
            </i>
          </button>
          {visibleCategories.map((c) => (
            <button
              key={c.id}
              className={`pill ${pool === c.id ? 'on' : ''}`}
              onClick={() => {
                setPool(c.id)
                setSeen(0)
              }}
            >
              {c.name}
              <i>{c.card_count}</i>
            </button>
          ))}
        </div>
        <div className="count">
          已复习 <b ref={countRef}>{seen}</b>
        </div>
      </div>

      <div className="tw" onMouseMove={onTiltMove} onMouseLeave={onTiltLeave}>
        <div className="stage" ref={stageRef}>
          {loading && <div className="skeleton" style={{ height: '100%' }} />}

          {!loading && error && (
            <div className="empty">
              <p>{error}</p>
              <button className="btn pri" onClick={() => void loadCard(pool)}>
                重试
              </button>
            </div>
          )}

          {empty && (
            <div className="empty">
              <p>这个分类还没有卡片</p>
              <button className="btn pri" onClick={() => setEditing(true)}>
                添加卡片
              </button>
              <button className="btn" style={{ marginLeft: 8 }} onClick={onGoCards}>
                去卡片列表
              </button>
            </div>
          )}

          {!loading && !error && card && (
            <>
              <i className="ghost g2" />
              <i className="ghost g1" />
              <div
                className={`card ${flipped ? 'flip' : ''}`}
                id="card"
                ref={cardRef}
                onClick={flip}
              >
                <div className="flipper">
                  <div
                    className="face"
                    style={{ ['--h' as string]: categoryHue(card.category_id) }}
                    data-ch={(nameOf(card.category_id) || '未')[0]}
                  >
                    <CategoryTag
                      name={nameOf(card.category_id)}
                      hue={categoryHue(card.category_id)}
                    />
                    <h2>{card.question}</h2>
                    <p className="hint">点击卡片或按空格查看答案</p>
                  </div>
                  <div
                    className="face back"
                    style={{ ['--h' as string]: categoryHue(card.category_id) }}
                    data-ch={(nameOf(card.category_id) || '未')[0]}
                  >
                    <CategoryTag
                      name={nameOf(card.category_id)}
                      hue={categoryHue(card.category_id)}
                    />
                    <h3>{card.question}</h3>
                    <div className="ans">
                      <Markdown source={card.answer} />
                    </div>
                  </div>
                </div>
              </div>
            </>
          )}
        </div>
      </div>

      <div className="ctl">
        <button className="btn" onClick={flip} disabled={!card}>
          {flipped ? '隐藏答案' : '显示答案'}
        </button>
        <button className="btn pri" onClick={() => void next()} disabled={!card}>
          下一张
        </button>
      </div>

      <p className="keys">
        <kbd>空格</kbd>翻面<kbd>→</kbd>下一张<kbd>E</kbd>编辑
        {poolCount !== undefined && `　本分类 ${poolCount} 张`}
      </p>

      {editing && card && (
        <CardForm
          categories={categories}
          card={card}
          onClose={() => setEditing(false)}
          onSaved={(saved) => {
            // Refresh in place so the flipped card shows the new text.
            setCard(saved)
            onDataChanged()
            toast('已保存')
          }}
        />
      )}

      {editing && !card && (
        <CardForm
          categories={categories}
          defaultCategoryId={pool === 'all' ? undefined : pool}
          onClose={() => setEditing(false)}
          onSaved={async () => {
            onDataChanged()
            toast('已添加')
            await loadCard(pool)
          }}
        />
      )}
    </div>
  )
}
