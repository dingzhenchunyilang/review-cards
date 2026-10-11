export interface Category {
  id: number
  name: string
  created_at: string
  card_count: number
}

export interface Card {
  id: number
  category_id: number
  question: string
  answer: string
  review_count: number
  created_at: string
  updated_at: string
}

export interface CardPage {
  items: Card[]
  total: number
  page: number
  page_size: number
}

export interface CardInput {
  question: string
  answer: string
  category_id: number
}

export const DEFAULT_CATEGORY_ID = 1
export const DEFAULT_CATEGORY_NAME = '未分类'
