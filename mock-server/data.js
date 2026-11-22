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
        sound_ids: ['sound-1', 'sound-2'],
        status: 'completed',
        audio_url: '/mock-audio/beat-1.wav',
      },
    ],

    // Fake YAMNet results, picked from what the model returned in our own testing
    classifications: [
      [{ label: 'Knock', score: 0.75 }, { label: 'Door', score: 0.45 }, { label: 'Tap', score: 0.2 }],
      [{ label: 'Finger snapping', score: 0.6 }, { label: 'Hands', score: 0.45 }, { label: 'Inside, small room', score: 0.22 }],
      [{ label: 'Rattle (instrument)', score: 0.45 }, { label: 'Maraca', score: 0.29 }, { label: 'Percussion', score: 0.26 }],
      [{ label: 'Drip', score: 0.53 }, { label: 'Liquid', score: 0.42 }, { label: 'Water', score: 0.39 }],
    ],
  }
}
