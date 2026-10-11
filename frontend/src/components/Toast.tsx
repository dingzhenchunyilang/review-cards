import { createContext, useCallback, useContext, useRef, useState, type ReactNode } from 'react'

interface Toast {
  id: number
  message: string
  undo?: () => void
}

interface ToastContextValue {
  toast: (message: string, undo?: () => void) => void
}

const ToastContext = createContext<ToastContextValue>({ toast: () => {} })

const UNDO_WINDOW_MS = 10000

export function ToastProvider({ children }: { children: ReactNode }) {
  const [toasts, setToasts] = useState<Toast[]>([])
  const nextId = useRef(1)
  const timers = useRef<Map<number, number>>(new Map())

  const dismiss = useCallback((id: number) => {
    const timer = timers.current.get(id)
    if (timer) {
      clearTimeout(timer)
      timers.current.delete(id)
    }
    setToasts((prev) => prev.filter((t) => t.id !== id))
  }, [])

  const toast = useCallback(
    (message: string, undo?: () => void) => {
      const id = nextId.current++
      setToasts((prev) => [...prev, { id, message, undo }])
      const timer = window.setTimeout(() => dismiss(id), undo ? UNDO_WINDOW_MS : 3200)
      timers.current.set(id, timer)
    },
    [dismiss],
  )

  const handleUndo = useCallback(
    (item: Toast) => {
      item.undo?.()
      dismiss(item.id)
    },
    [dismiss],
  )

  return (
    <ToastContext.Provider value={{ toast }}>
      {children}
      {toasts.map((item) => (
        <div className="toast" key={item.id}>
          <span>{item.message}</span>
          {item.undo && <button onClick={() => handleUndo(item)}>撤销</button>}
        </div>
      ))}
    </ToastContext.Provider>
  )
}

// eslint-disable-next-line react-refresh/only-export-components
export function useToast() {
  return useContext(ToastContext)
}
