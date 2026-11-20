import { createClient } from '@supabase/supabase-js'

// the one supabase client the browser uses (session.tsx signs in with it)
// it's null when the keys aren't set so guest and dev mode still work
const url = import.meta.env.VITE_SUPABASE_URL
const key = import.meta.env.VITE_SUPABASE_ANON_KEY
const configured = Boolean(url && key && !url.includes('your-project') && !key.includes('your-anon-key'))

export const supabase = configured ? createClient(url, key) : null
