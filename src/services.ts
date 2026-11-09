import type { SoundView } from './model';

export class ServiceNotConfiguredError extends Error {
  readonly code = 'SERVICE_NOT_CONFIGURED';

  constructor(service: string) {
    super(`${service} is not connected yet. Replace the stub adapter with the production integration.`);
    this.name = 'ServiceNotConfiguredError';
  }
}

export interface BeatParameters {
  tempo: number;
  genre: string;
  ensemble: string;
  meter: string;
  key: string;
  mode: string;
  instruments: Record<string, string>;
}

export interface BeatOutput {
  id: string;
  name: string;
  audioUrl: string;
  durationSeconds: number;
  waveform: number[];
  downloadUrl: string;
}

export interface ProfileRecord {
  username: string;
  email: string;
  photoUrl?: string;
}

export interface AuthService {
  signInWithGoogle(): Promise<void>;
  signOut(): Promise<void>;
}

export interface SoundService {
  list(input: { scope: 'mine' | 'public'; query?: string }): Promise<SoundView[]>;
  getPlaybackUrl(soundId: string): Promise<string>;
  uploadRecording(input: { name: string; blob: Blob }): Promise<SoundView>;
  delete(soundId: string): Promise<void>;
  setVisibility(soundId: string, visibility: SoundView['visibility']): Promise<SoundView>;
  report(soundId: string, reason: string): Promise<void>;
}

export interface BeatService {
  generate(input: { soundIds: string[]; parameters: BeatParameters }): Promise<BeatOutput>;
  getOutput(beatId: string): Promise<BeatOutput>;
  getExportUrl(beatId: string): Promise<string>;
}

export interface ProfileService {
  get(): Promise<ProfileRecord>;
  update(profile: ProfileRecord): Promise<ProfileRecord>;
  uploadPhoto(file: File): Promise<string>;
}

const unavailable = (service: string) => async (): Promise<never> => {
  throw new ServiceNotConfiguredError(service);
};

// Production adapters should preserve these interfaces. The auth implementation is
// intentionally Supabase-shaped without importing or initializing a client yet.
export const authService: AuthService = {
  signInWithGoogle: unavailable('Supabase Google sign-in'),
  signOut: unavailable('Supabase sign-out'),
};

export const soundService: SoundService = {
  list: unavailable('Sound library API'),
  getPlaybackUrl: unavailable('Sound playback API'),
  uploadRecording: unavailable('Sound upload API'),
  delete: unavailable('Sound deletion API'),
  setVisibility: unavailable('Sound visibility API'),
  report: unavailable('Sound reporting API'),
};

export const beatService: BeatService = {
  generate: unavailable('Beat generation API'),
  getOutput: unavailable('Beat output API'),
  getExportUrl: unavailable('Beat export API'),
};

export const profileService: ProfileService = {
  get: unavailable('Profile API'),
  update: unavailable('Profile update API'),
  uploadPhoto: unavailable('Profile photo API'),
};

export function serviceErrorMessage(error: unknown) {
  if (error instanceof Error) return error.message;
  return 'Something went wrong. Please try again.';
}
