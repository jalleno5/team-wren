import type { SoundView } from './model';

export class ServiceNotConfiguredError extends Error {
  readonly code = 'SERVICE_NOT_CONFIGURED';
  constructor(service: string) {
    super(`${service} is not connected yet. Add the Supabase environment variables or replace the stub adapter.`);
    this.name = 'ServiceNotConfiguredError';
  }
}

export interface BeatParameters { tempo:number; lengthBars:number; genre:string; ensemble:string; meter:string; key:string; mode:string; instruments:Record<string,string> }
export interface BeatOutput { id:string; name:string; audioUrl:string; durationSeconds:number; waveform:number[]; downloadUrl:string }
export interface ProfileRecord { username:string; email:string; photoUrl?:string }
export interface SoundPlayback { url:string; trimStartSeconds:number; trimEndSeconds?:number }
export interface SoundFlag { id:string; soundId:string; reason:string; status:'open'|'reviewed'|'dismissed'; createdAt:string }

export interface AuthService { signInWithGoogle():Promise<void>; signOut():Promise<void> }
export interface SoundService {
  list(input:{scope:'mine'|'public';query?:string}):Promise<SoundView[]>;
  getPlayback(soundId:string):Promise<SoundPlayback>;
  uploadRecording(input:{name:string;blob:Blob;trimStartSeconds:number;trimEndSeconds:number}):Promise<SoundView>;
  delete(soundId:string):Promise<void>;
  setVisibility(soundId:string,visibility:SoundView['visibility']):Promise<SoundView>;
  flag(soundId:string,reason:string):Promise<SoundFlag>;
}
export interface BeatService { generate(input:{soundIds:string[];parameters:BeatParameters}):Promise<BeatOutput>; getOutput(beatId:string):Promise<BeatOutput>; getExportUrl(beatId:string):Promise<string> }
export interface ProfileService { get():Promise<ProfileRecord>; update(profile:ProfileRecord):Promise<ProfileRecord>; uploadPhoto(file:File):Promise<string> }

const unavailable=(service:string)=>async():Promise<never>=>{throw new ServiceNotConfiguredError(service);};
const supabaseUrl=(import.meta.env.VITE_SUPABASE_URL as string|undefined)?.replace(/\/$/,'');
const supabaseKey=import.meta.env.VITE_SUPABASE_ANON_KEY as string|undefined;
const soundBucket=(import.meta.env.VITE_SUPABASE_SOUND_BUCKET as string|undefined)||'sounds';
const configured=Boolean(supabaseUrl&&supabaseKey);

function headers(extra:HeadersInit={}) {
  return {apikey:supabaseKey!,Authorization:`Bearer ${supabaseKey}`,'Content-Type':'application/json',...extra};
}
async function request<T>(path:string,init:RequestInit={}):Promise<T> {
  const response=await fetch(`${supabaseUrl}${path}`,{...init,headers:headers(init.headers)});
  if(!response.ok)throw new Error(`Backend request failed (${response.status}).`);
  if(response.status===204)return undefined as T;
  return response.json() as Promise<T>;
}
type SoundRow={id:string;name:string;creator:string;owned:boolean;visibility:'private'|'public';waveform:number[]|null;audio_url?:string|null;trim_start_seconds?:number|null;trim_end_seconds?:number|null};
const toSound=(row:SoundRow):SoundView=>({id:row.id,name:row.name,creator:row.creator,owned:row.owned,visibility:row.visibility,waveform:row.waveform??[],audioUrl:row.audio_url??undefined,trimStartSeconds:row.trim_start_seconds??0,trimEndSeconds:row.trim_end_seconds??undefined});

const supabaseSoundService:SoundService={
  async list({scope,query}) {
    const params=new URLSearchParams({select:'id,name,creator,owned,visibility,waveform,audio_url,trim_start_seconds,trim_end_seconds',order:'created_at.desc'});
    params.set(scope==='mine'?'owned':'visibility',scope==='mine'?'eq.true':'eq.public');
    if(query?.trim())params.set('name',`ilike.*${query.trim()}*`);
    return (await request<SoundRow[]>(`/rest/v1/sounds?${params}`)).map(toSound);
  },
  async getPlayback(soundId) {
    const params=new URLSearchParams({select:'audio_url,trim_start_seconds,trim_end_seconds',id:`eq.${soundId}`,limit:'1'});
    const [row]=await request<Array<Pick<SoundRow,'audio_url'|'trim_start_seconds'|'trim_end_seconds'>>>(`/rest/v1/sounds?${params}`);
    if(!row?.audio_url)throw new Error('This sample does not have a playable audio file.');
    return {url:row.audio_url,trimStartSeconds:row.trim_start_seconds??0,trimEndSeconds:row.trim_end_seconds??undefined};
  },
  async uploadRecording({name,blob,trimStartSeconds,trimEndSeconds}) {
    const objectName=`${crypto.randomUUID()}.${blob.type.includes('ogg')?'ogg':'webm'}`;
    const upload=await fetch(`${supabaseUrl}/storage/v1/object/${soundBucket}/${objectName}`,{method:'POST',headers:{apikey:supabaseKey!,Authorization:`Bearer ${supabaseKey}`,'Content-Type':blob.type||'audio/webm','x-upsert':'false'},body:blob});
    if(!upload.ok)throw new Error(`Sound upload failed (${upload.status}).`);
    const audioUrl=`${supabaseUrl}/storage/v1/object/public/${soundBucket}/${objectName}`;
    const [row]=await request<SoundRow[]>('/rest/v1/sounds',{method:'POST',headers:{Prefer:'return=representation'},body:JSON.stringify({name,audio_url:audioUrl,trim_start_seconds:trimStartSeconds,trim_end_seconds:trimEndSeconds,visibility:'private',waveform:[]})});
    return toSound(row);
  },
  async delete(soundId){await request<void>(`/rest/v1/sounds?id=eq.${encodeURIComponent(soundId)}`,{method:'DELETE'});},
  async setVisibility(soundId,visibility){const [row]=await request<SoundRow[]>(`/rest/v1/sounds?id=eq.${encodeURIComponent(soundId)}`,{method:'PATCH',headers:{Prefer:'return=representation'},body:JSON.stringify({visibility})});return toSound(row);},
  async flag(soundId,reason){const [row]=await request<Array<{id:string;sound_id:string;reason:string;status:SoundFlag['status'];created_at:string}>>('/rest/v1/sound_flags',{method:'POST',headers:{Prefer:'return=representation'},body:JSON.stringify({sound_id:soundId,reason,status:'open'})});return {id:row.id,soundId:row.sound_id,reason:row.reason,status:row.status,createdAt:row.created_at};},
};

export const authService:AuthService={signInWithGoogle:unavailable('Supabase Google sign-in'),signOut:unavailable('Supabase sign-out')};
export const soundService:SoundService=configured?supabaseSoundService:{list:unavailable('Sound library API'),getPlayback:unavailable('Sound playback API'),uploadRecording:unavailable('Sound upload API'),delete:unavailable('Sound deletion API'),setVisibility:unavailable('Sound visibility API'),flag:unavailable('Sound flagging API')};
export const beatService:BeatService={generate:unavailable('Beat generation API'),getOutput:unavailable('Beat output API'),getExportUrl:unavailable('Beat export API')};
export const profileService:ProfileService={get:unavailable('Profile API'),update:unavailable('Profile update API'),uploadPhoto:unavailable('Profile photo API')};
export function serviceErrorMessage(error:unknown){return error instanceof Error?error.message:'Something went wrong. Please try again.';}
