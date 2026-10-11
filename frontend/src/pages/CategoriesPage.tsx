import { useEffect, useRef, useState } from 'react'
import { api } from '../api/client'
import type { Category } from '../api/types'
import { CategoryDot } from '../components/Markdown'
import { ConfirmDialog } from '../components/Modal'
import { useToast } from '../components/Toast'
import { DEFAULT_CATEGORY_ID, DEFAULT_CATEGORY_NAME } from '../api/types'
import { categoryHue } from '../utils'

interface Props {
  categories: Category[]
  onDataChanged: () => void
}

export function CategoriesPage({ categories, onDataChanged }: Props) {
  const { toast } = useToast()
  const [newName, setNewName] = useState('')
  const [editingId, setEditingId] = useState<number | null>(null)
  const [editingName, setEditingName] = useState('')
  const [deleting, setDeleting] = useState<Category | null>(null)
  const editInputRef = useRef<HTMLInputElement>(null)

  useEffect(() => {
    if (editingId !== null) {
      editInputRef.current?.focus()
      editInputRef.current?.select()
    }
  }, [editingId])

  const add = async () => {
    const value = newName.trim()
    if (!value) return
    try {
      await api.createCategory(value)
      setNewName('')
      onDataChanged()
      toast('已添加分类')
    } catch (e) {
      toast(e instanceof Error ? e.message : '添加失败')
    }
  }

  const saveRename = async (original: Category) => {
    const value = editingName.trim()
    setEditingId(null)
    if (!value || value === original.name) return
    try {
      await api.renameCategory(original.id, value)
      onDataChanged()
      toast('已重命名')
    } catch (e) {
      toast(e instanceof Error ? e.message : '重命名失败')
    }
  }

  const remove = async (category: Category) => {
    try {
      await api.deleteCategory(category.id)
      onDataChanged()
      toast('已删除分类')
    } catch (e) {
      toast(e instanceof Error ? e.message : '删除失败')
    }
  }

  const isDefault = (id: number) => id === DEFAULT_CATEGORY_ID

  return (
    <div className="view">
      <h1>分类</h1>

      <div className="tool">
        <input
          placeholder="新分类名称，回车添加"
          value={newName}
          onChange={(e) => setNewName(e.target.value)}
          onKeyDown={(e) => {
            if (e.key === 'Enter') void add()
          }}
        />
        <button className="btn pri" onClick={() => void add()}>
          添加
        </button>
      </div>

      {categories.length === 0 && (
        <div className="empty">
          <p>还没有分类</p>
        </div>
      )}

      {categories.map((c) => (
        <div className="cr" key={c.id}>
          <CategoryDot hue={categoryHue(c.id)} />
          <span className="nm">
            {editingId === c.id ? (
              <input
                ref={editInputRef}
                value={editingName}
                onChange={(e) => setEditingName(e.target.value)}
                onKeyDown={(e) => {
                  if (e.key === 'Enter') void saveRename(c)
                  if (e.key === 'Escape') setEditingId(null)
                }}
                onBlur={() => void saveRename(c)}
              />
            ) : (
              c.name
            )}
          </span>
          <span className="meta" style={{ display: 'inline' }}>
            {c.card_count} 张
          </span>
          {!isDefault(c.id) && (
            <>
              <button
                className="btn sm"
                onClick={() => {
                  setEditingId(c.id)
                  setEditingName(c.name)
                }}
              >
                重命名
              </button>
              <button className="btn sm del" onClick={() => setDeleting(c)}>
                删除
              </button>
            </>
          )}
          {isDefault(c.id) && (
            <span className="meta" style={{ display: 'inline' }}>
              默认
            </span>
          )}
        </div>
      ))}

      {deleting && (
        <ConfirmDialog
          title={
            `删除「${deleting.name}」？` +
            (deleting.card_count > 0
              ? `其中 ${deleting.card_count} 张卡片会移入「${DEFAULT_CATEGORY_NAME}」。`
              : '')
          }
          onConfirm={() => void remove(deleting)}
          onClose={() => setDeleting(null)}
        />
      )}
    </div>
  )
}
