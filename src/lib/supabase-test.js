import { supabase } from './supabase';

const tables = ['users', 'sounds', 'beats', 'sounds_beats', 'sound_reports']

export async function testSupabaseConnections() {
    for (const table of tables) {
        const { data, error } = await supabase
            .from(table)
            .select('*')
        
        if (error) {
            console.error(`Supabase error on ${table} table:`, error.message)
            continue
        }

        console.log(`Supabase data retrieved from ${table} table:`, data)
    }
}