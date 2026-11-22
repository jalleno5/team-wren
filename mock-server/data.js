// Fake data for the mock API. Field names match our Supabase tables,
// plus `visibility`, which the database policies already use.

// Everyone using the mock API is signed in as this user
export const CURRENT_USER_ID = 'user-1'

// Returns a fresh copy each time, so every server start (and every test)
// begins with the same data
export function createData() {
  return {
    profile: {
      id: CURRENT_USER_ID,
      username: 'demo_user',
      email: 'demo@example.com',
      avatar_url: null,
      created_at: '2026-11-01T12:00:00.000Z',
    },

    sounds: [
      { id: 'sound-1', user_id: CURRENT_USER_ID, title: 'Coffee tin kick', visibility: 'private' },
      { id: 'sound-2', user_id: CURRENT_USER_ID, title: 'Keys on the counter', visibility: 'private' },
      { id: 'sound-3', user_id: CURRENT_USER_ID, title: 'Pen click', visibility: 'public' },
      { id: 'sound-4', user_id: 'user-2', title: 'Bottle cap snap', visibility: 'public' },
      { id: 'sound-5', user_id: 'user-3', title: 'Paper bag shuffle', visibility: 'public' },
    ],

    sound_reports: [],

    beats: [
      {
        id: 'beat-1',
        user_id: CURRENT_USER_ID,
        title: 'Kitchen groove',
        speed: 100,
        genre: 'popular',
        visibility: 'private',
        sounds: [
          { sound_id: 'sound-1', category: 'percussion' },
          { sound_id: 'sound-2', category: 'melodic' },
        ],
        status: 'completed',
        audio_url: '/mock-audio/beat-1.wav',
      },
    ],

    classifications: ['percussion', 'rhythmic', 'melodic', 'ambient', 'transition'],
  }
}
