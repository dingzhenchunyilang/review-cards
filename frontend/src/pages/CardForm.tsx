import { useEffect, useRef, useState } from 'react'
import { api } from '../api/client'
import type { Card, Category } from '../api/types'
import { Modal } from '../components/Modal'
import { Markdown } from '../components/Markdown'

interface Props {
  categories: Category[]
  card?: Card | null
  /** Category preselected when creating a new card. */
  defaultCategoryId?: number
  onClose: () => void
  /** Receives the saved card so callers can refresh in place. */
  onSaved: (card: Card) => void
  onError?: (message: string) => void
}

export function CardForm({
  categories,
  card,
  defaultCategoryId,
  onClose,
  onSaved,
  onError,
}: Props) {
  const editing = Boolean(card)
  const questionRef = useRef<HTMLTextAreaElement>(null)

  // Focus after a tick instead of using autoFocus. The review page opens this
  // form from the "E" keystroke, and an immediate focus would let that same
  // keystroke land inside the textarea as a stray character. The prototype
  // works around it the same way (setTimeout 50ms).
  useEffect(() => {
    const timer = window.setTimeout(() => questionRef.current?.focus(), 50)
    return () => window.clearTimeout(timer)
  }, [])

  const [categoryId, setCategoryId] = useState<number>(
    card?.category_id ?? defaultCategoryId ?? categories[0]?.id ?? 1,
  )
  const [question, setQuestion] = useState(card?.question ?? '')
  const [answer, setAnswer] = useState(card?.answer ?? '')
  const [preview, setPreview] = useState(false)
  const [questionError, setQuestionError] = useState('')
  const [answerError, setAnswerError] = useState('')
  const [submitError, setSubmitError] = useState('')
  const [saving, setSaving] = useState(false)

  const validate = () => {
    const q = question.trim()
    const a = answer.trim()
    setQuestionError(q ? '' : '请填写题目')
    setAnswerError(a ? '' : '请填写答案')
    return Boolean(q && a)
  }

  const submit = async (keepOpen: boolean) => {
    if (!validate() || saving) return
    setSaving(true)
    setSubmitError('')
    try {
      const payload = {
        question: question.trim(),
        answer: answer.trim(),
        category_id: categoryId,
      }
      const saved =
        editing && card
          ? await api.updateCard(card.id, payload)
          : await api.createCard(payload)
      onSaved(saved)
      if (keepOpen) {
        setQuestion('')
        setAnswer('')
        setPreview(false)
      } else {
        onClose()
      }
    } catch (e) {
      const message = e instanceof Error ? e.message : '保存失败'
      setSubmitError(message)
      onError?.(message)
    } finally {
      setSaving(false)
    }
  }

  return (
    <Modal
      title={editing ? '编辑卡片' : '新增卡片'}
      onClose={onClose}
      footer={
        <>
          <button className="btn" onClick={onClose}>
            取消
          </button>
          {!editing && (
            <button className="btn" onClick={() => void submit(true)} disabled={saving}>
              保存并继续添加
            </button>
          )}
          <button className="btn pri" onClick={() => void submit(false)} disabled={saving}>
            {saving ? '保存中…' : '保存'}
          </button>
        </>
      }
    >
      <label className="fld">
        分类
        <select value={categoryId} onChange={(e) => setCategoryId(Number(e.target.value))}>
          {categories.map((c) => (
            <option key={c.id} value={c.id}>
              {c.name}
            </option>
          ))}
        </select>
      </label>

      <label className="fld">
        题目
        <textarea
          rows={3}
          value={question}
          ref={questionRef}
          onChange={(e) => setQuestion(e.target.value)}
          onKeyDown={(e) => {
            if (e.key === 'Enter' && (e.ctrlKey || e.metaKey)) void submit(false)
          }}
        />
        <span className="err">{questionError}</span>
      </label>

      <div className="tabs">
        <button className={preview ? '' : 'on'} onClick={() => setPreview(false)}>
          编辑
        </button>
        <button className={preview ? 'on' : ''} onClick={() => setPreview(true)}>
          预览
        </button>
      </div>

      {!preview && (
        <textarea
          rows={8}
          style={{ width: '100%' }}
          value={answer}
          onChange={(e) => setAnswer(e.target.value)}
          onKeyDown={(e) => {
            if (e.key === 'Enter' && (e.ctrlKey || e.metaKey)) void submit(false)
          }}
        />
      )}
      {preview && (
        // Prototype renders the preview as a bare `.md` block (no border), so the
        // rendered markdown lines up with how it will look on the card.
        <div className="md" style={{ minHeight: 180 }}>
          {answer.trim() ? (
            <Markdown source={answer} />
          ) : (
            <p style={{ color: 'var(--mute)', margin: 0 }}>还没有内容</p>
          )}
        </div>
      )}
      <span className="err">{answerError || submitError}</span>
    </Modal>
  )
}
