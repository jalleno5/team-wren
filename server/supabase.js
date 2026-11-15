// connects to supabase as the person who sent the request

import {createClient} from '@supabase/supabase-js'
import { HttpError } from './http.js'

// process.env holds values from .env.local
const SUPABASE_URL = process.env.VITE_SUPABASE_URL
const SUPABASE_ANON_KEY = process.env.VITE_SUPABASE_ANON_KEY

if (!SUPABASE_URL || !SUPABASE_ANON_KEY) {
  throw new Error('Set VITE_SUPABASE_URL and VITE_SUPABASE_ANON_KEY in .env.local')
}

// pulls out user token (frontend sends the header "Authorization: Bearer <token>")
function readToken(request) {
    const [scheme, token] = (request.headers.authorization ?? '').split(' ')
    return scheme === 'Bearer' && token ? token : null
}

// returns { db, user }
// db is a superbase client that acts as this user or as a gust
// user is the logged-in user, null for guest
export async function connectAs(request) {
    const token = readToken(request)
    const db = createClient(SUPABASE_URL, SUPABASE_ANON_KEY, {
        // server handles many people so don't save any one person's login
        auth: { persistSession: false, autoRefreshToken: false },
        // attach user's token to every database/storage request this client makes
        global: token ? { headers: { Authorization: `Bearer ${token}` } } : undefined,
    })

    if (!token) return {db, user:null}

    //ask supabase is this token real and whose is it (JWT check)
    const {data, error} = await db.auth.getUser(token)
    if (error || !data.user) {
        throw new HttpError(401, 'Your session has expired. Please sign in again.')
    }
    return { db, user: data.user }
}

