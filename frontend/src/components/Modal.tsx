import { useEffect, type ReactNode } from 'react'

interface ModalProps {
  title: string
  onClose: () => void
  children?: ReactNode
  footer?: ReactNode
}

export function Modal({ title, onClose, children, footer }: ModalProps) {
  useEffect(() => {
    const onKey = (e: KeyboardEvent) => {
      if (e.key === 'Escape') onClose()
    }
    window.addEventListener('keydown', onKey)
    return () => window.removeEventListener('keydown', onKey)
  }, [onClose])

  return (
    <div
      className="ov"
      onMouseDown={(e) => {
        if (e.target === e.currentTarget) onClose()
      }}
    >
      <div className="dlg" role="dialog" aria-modal="true" aria-label={title}>
        <h3>{title}</h3>
        {children}
        {footer && <div className="dact">{footer}</div>}
      </div>
    </div>
  )
}

interface ConfirmProps {
  title: string
  confirmText?: string
  onConfirm: () => void
  onClose: () => void
}

export function ConfirmDialog({
  title,
  confirmText = '确认删除',
  onConfirm,
  onClose,
}: ConfirmProps) {
  return (
    <Modal
      title={title}
      onClose={onClose}
      footer={
        <>
          <button className="btn" onClick={onClose}>
            取消
          </button>
          <button
            className="btn pri"
            onClick={() => {
              onConfirm()
              onClose()
            }}
          >
            {confirmText}
          </button>
        </>
      }
    />
  )
}
