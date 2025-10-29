import { createClient } from '@supabase/supabase-js'

// For client-side access, Next.js requires NEXT_PUBLIC_ prefix
// But Vercel environment variables are set without prefix
// So we check both
const supabaseUrl = 
  process.env.NEXT_PUBLIC_SUPABASE_URL || 
  (typeof window === 'undefined' ? process.env.SUPABASE_URL : '') || 
  ''

const supabaseKey = 
  process.env.NEXT_PUBLIC_SUPABASE_KEY || 
  (typeof window === 'undefined' ? process.env.SUPABASE_KEY : '') || 
  ''

if (!supabaseUrl || !supabaseKey) {
  console.error('Missing Supabase environment variables')
  console.error('Set SUPABASE_URL and SUPABASE_KEY in Vercel or .env.local')
}

export const supabase = createClient(
  supabaseUrl || 'https://placeholder.supabase.co',
  supabaseKey || 'placeholder-key'
)

// Database types (will be auto-generated later)
export type Student = {
  id: string
  email: string
  name: string
  academic_year: string
  year_group: string
  establishment_id: string
  knack_id: string
  created_at: string
  updated_at: string
}

export type VESPAScore = {
  id: string
  student_id: string
  cycle: number
  academic_year: string
  vision: number | null
  effort: number | null
  systems: number | null
  practice: number | null
  attitude: number | null
  overall: number | null
  completion_date: string | null
  created_at: string
}

export type QuestionResponse = {
  id: string
  student_id: string
  cycle: number
  academic_year: string
  question_id: string
  response_value: number
  created_at: string
}

export type Establishment = {
  id: string
  knack_id: string
  name: string
  is_australian: boolean
  created_at: string
}

