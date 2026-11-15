import { supabase } from './supabase';

const tables = ['users', 'sounds', 'beats', 'sounds_beats', 'sound_reports']

export async function testSupabaseConnections() {
    // no client when the keys aren't in .env.local
    if (!supabase) return console.error('Supabase keys are not set in .env.local')

    for (const table of tables) {
        const { data, error } = await supabase
            .from(table)
            // users hides the email column, so '*' would be refused there; ask only for allowed columns
            .select(table === 'users' ? 'id, username' : '*')
        
        if (error) {
            console.error(`Supabase error on ${table} table:`, error.message)
            continue
        }

        console.log(`Supabase data retrieved from ${table} table:`, data)
    }
}