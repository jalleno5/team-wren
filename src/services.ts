import { isSoundCategory, type SoundCategory, type SoundView } from './model';

export class ServiceNotConfiguredError extends Error {
  readonly code='SERVICE_NOT_CONFIGURED';
  constructor(service:string){super(`${service} is not configured.`);this.name='ServiceNotConfiguredError';}
}
export class ApiError extends Error {
  readonly code='API_ERROR';
  constructor(readonly status:number,message:string,readonly path:string){super(message);this.name='ApiError';}
}
export class BackendCapabilityError extends Error {
  readonly code='BACKEND_CAPABILITY_MISSING';
  constructor(readonly capability:string){super(`${capability} is not implemented by the current mock backend.`);this.name='BackendCapabilityError';}
}

export interface BeatParameters { tempo:number; genre:string }
export type BeatStatus='queued'|'processing'|'completed'|'failed';
export interface BeatJobReference { id:string; status:BeatStatus; guestToken?:string }
export interface BeatOutput { id:string; name:string; status:BeatStatus; audioUrl?:string; durationSeconds:number; waveform:number[]; error?:string }
export interface ProfileRecord { id:string; username:string; email:string; photoUrl?:string }
export interface SoundPlayback { url:string; trimStartSeconds:number; trimEndSeconds?:number }
export interface SoundReport { id:string; soundId:string; description:string|null; createdAt:string }
export interface CategorizedSound { soundId:string; category:SoundCategory }

export interface SoundService {
  list(input:{scope:'mine'|'public';query?:string;signal?:AbortSignal}):Promise<SoundView[]>;
  getPlayback(soundId:string,signal?:AbortSignal):Promise<SoundPlayback>;
  uploadRecording(input:{name:string;blob:Blob;trimStartSeconds:number;trimEndSeconds:number}):Promise<SoundView>;
  delete(soundId:string):Promise<void>;
  setVisibility(soundId:string,visibility:SoundView['visibility']):Promise<SoundView>;
  flag(soundId:string,reason:string):Promise<SoundReport>;
  classify(soundId:string):Promise<SoundCategory>;
}
export interface BeatService {
  generate(input:{sounds:CategorizedSound[];parameters:BeatParameters;guest:boolean;title?:string}):Promise<BeatJobReference>;
  getOutput(beatId:string,input?:{guestToken?:string;signal?:AbortSignal}):Promise<BeatOutput>;
  claim(beatId:string,guestToken:string):Promise<BeatOutput>;
  getDownloadUrl(beatId:string):Promise<string>;
}
export interface ProfileService { get(signal?:AbortSignal):Promise<ProfileRecord>; update(profile:{username:string}):Promise<ProfileRecord>; uploadPhoto(file:File):Promise<string> }

type TokenProvider=()=>Promise<string|undefined>;
let tokenProvider:TokenProvider=async()=>undefined;
export function setAccessTokenProvider(provider:TokenProvider){tokenProvider=provider;}

const apiBase=((import.meta.env.VITE_API_BASE_URL as string|undefined)?.replace(/\/$/,'')||'/api');
const apiOrigin=/^https?:\/\//.test(apiBase)?new URL(apiBase).origin:window.location.origin;
const absoluteUrl=(value:string)=>{try{return new URL(value,apiOrigin).toString();}catch{return value;}};

async function apiRequest<T>(path:string,init:RequestInit={},guestToken?:string):Promise<T>{
  const token=await tokenProvider();
  const headers=new Headers(init.headers);
  if(init.body&&!headers.has('Content-Type')&&typeof init.body==='string')headers.set('Content-Type','application/json');
  if(token)headers.set('Authorization',`Bearer ${token}`);
  if(guestToken)headers.set('X-Guest-Job-Token',guestToken);
  let response:Response;
  try{response=await fetch(`${apiBase}${path}`,{...init,headers});}
  catch{throw new ApiError(0,'The API could not be reached. Start the mock API or configure VITE_API_BASE_URL.',path);}
  if(response.status===204)return undefined as T;
  const contentType=response.headers.get('content-type')??'';
  let body:unknown;
  if(contentType.includes('application/json')){
    try{body=await response.json();}catch{throw new ApiError(response.status,'The API returned malformed JSON.',path);}
  }else{
    const responseText=await response.text();
    if(response.ok)throw new ApiError(response.status,'The API returned a non-JSON response.',path);
    body=responseText?{error:responseText}:undefined;
  }
  if(!response.ok){
    const message=typeof body==='object'&&body&&'error' in body&&typeof body.error==='string'?body.error:response.status===500&&!body?'The API could not be reached. Start the mock API or configure VITE_API_BASE_URL.':`Backend request failed (${response.status}).`;
    throw new ApiError(response.status,message,path);
  }
  if(body===undefined)throw new ApiError(response.status,'The API returned an empty response.',path);
  return body as T;
}

async function capability<T>(name:string,operation:()=>Promise<T>):Promise<T>{
  try{return await operation();}catch(error){if(error instanceof ApiError&&error.status===404)throw new BackendCapabilityError(name);throw error;}
}

type ProfileDto={id:string;username:string;email:string;avatar_url?:string|null};
type SoundDto={id:string;user_id:string;title:string;visibility:'private'|'public';creator?:string;waveform?:number[];audio_url?:string|null;trim_start_seconds?:number|null;trim_end_seconds?:number|null};
type ReportDto={id:string;sound_id:string;description?:string|null;created_at:string};
type BeatDto={id:string;title?:string;status:BeatStatus;audio_url?:string|null;duration_seconds?:number;waveform?:number[];error?:string};
let currentProfile:ProfileRecord|undefined;

function decorativeWaveform(seed:string){
  let value=[...seed].reduce((sum,char)=>sum+char.charCodeAt(0),17);
  return Array.from({length:24},()=>{value=(value*9301+49297)%233280;return .12+(value/233280)*.82;});
}
function toSound(row:SoundDto,scope:'mine'|'public'):SoundView{
  const owned=currentProfile?row.user_id===currentProfile.id:scope==='mine';
  return {id:row.id,name:row.title,creator:row.creator??(owned?(currentProfile?.username??'You'):'Community member'),owned,visibility:row.visibility,waveform:row.waveform?.length?row.waveform:decorativeWaveform(row.id),audioUrl:row.audio_url??undefined,trimStartSeconds:row.trim_start_seconds??0,trimEndSeconds:row.trim_end_seconds??undefined};
}
function toProfile(row:ProfileDto):ProfileRecord{return {id:row.id,username:row.username,email:row.email,photoUrl:row.avatar_url??undefined};}
function toBeat(row:BeatDto):BeatOutput{return {id:row.id,name:row.title?.trim()||'Untitled beat',status:row.status,audioUrl:row.audio_url?absoluteUrl(row.audio_url):undefined,durationSeconds:row.duration_seconds??0,waveform:row.waveform?.length?row.waveform:decorativeWaveform(row.id),error:row.error};}

export const profileService:ProfileService={
  async get(signal){const profile=toProfile(await apiRequest<ProfileDto>('/profile',{signal}));currentProfile=profile;return profile;},
  async update({username}){const profile=toProfile(await apiRequest<ProfileDto>('/profile',{method:'PATCH',body:JSON.stringify({username})}));currentProfile=profile;return profile;},
  async uploadPhoto(file){
    return capability('Profile photo upload',async()=>{
      const signed=await apiRequest<{upload_url:string;storage_path:string;headers?:Record<string,string>}>('/uploads',{method:'POST',body:JSON.stringify({purpose:'avatar',content_type:file.type,size_bytes:file.size})});
      const upload=await fetch(signed.upload_url,{method:'PUT',headers:signed.headers,body:file});if(!upload.ok)throw new ApiError(upload.status,'The profile photo upload failed.','/uploads');
      await apiRequest('/profile',{method:'PATCH',body:JSON.stringify({avatar_url:signed.storage_path})});return signed.storage_path;
    });
  },
};

export const soundService:SoundService={
  async list({scope,query,signal}){
    if(scope==='mine'&&!currentProfile)try{await profileService.get(signal);}catch{/* the list can still mark every mine row as owned */}
    const rows=await apiRequest<SoundDto[]>(`/sounds?scope=${scope}`,{signal});
    const mapped=rows.map(row=>toSound(row,scope));const term=query?.trim().toLowerCase();return term?mapped.filter(sound=>sound.name.toLowerCase().includes(term)):mapped;
  },
  async getPlayback(soundId,signal){return capability('Sound playback metadata',async()=>{const row=await apiRequest<{url:string;trim_start_seconds?:number;trim_end_seconds?:number}>(`/sounds/${encodeURIComponent(soundId)}/playback`,{signal});return {url:absoluteUrl(row.url),trimStartSeconds:row.trim_start_seconds??0,trimEndSeconds:row.trim_end_seconds};});},
  async uploadRecording({name,blob,trimStartSeconds,trimEndSeconds}){
    return capability('Recorded sound upload',async()=>{
      const signed=await apiRequest<{upload_url:string;storage_path:string;headers?:Record<string,string>}>('/uploads',{method:'POST',body:JSON.stringify({purpose:'sound',content_type:blob.type||'audio/webm',size_bytes:blob.size})});
      const upload=await fetch(signed.upload_url,{method:'PUT',headers:signed.headers,body:blob});if(!upload.ok)throw new ApiError(upload.status,'The sound upload failed.','/uploads');
      const row=await apiRequest<SoundDto>('/sounds',{method:'POST',body:JSON.stringify({title:name,storage_path:signed.storage_path,source_type:'recorded',duration_in_ms:Math.round((trimEndSeconds-trimStartSeconds)*1000),trim_start_ms:Math.round(trimStartSeconds*1000),trim_end_ms:Math.round(trimEndSeconds*1000)})});return toSound(row,'mine');
    });
  },
  async delete(soundId){await apiRequest<void>(`/sounds/${encodeURIComponent(soundId)}`,{method:'DELETE'});},
  async setVisibility(soundId,visibility){return toSound(await apiRequest<SoundDto>(`/sounds/${encodeURIComponent(soundId)}`,{method:'PATCH',body:JSON.stringify({visibility})}),'mine');},
  async flag(soundId,reason){const row=await apiRequest<ReportDto>(`/sounds/${encodeURIComponent(soundId)}/reports`,{method:'POST',body:JSON.stringify({description:reason})});return {id:row.id,soundId:row.sound_id,description:row.description??null,createdAt:row.created_at};},
  async classify(soundId){const row=await apiRequest<{sound_id:string;category:unknown}>('/classify',{method:'POST',body:JSON.stringify({sound_id:soundId})});if(row.sound_id!==soundId||!isSoundCategory(row.category))throw new ApiError(502,'The classifier returned an invalid sound category.','/classify');return row.category;},
};

export const beatService:BeatService={
  async generate({sounds,parameters,guest,title}){
    const row=await apiRequest<{id:string;status:BeatStatus;guest_token?:string}>('/beats',{method:'POST',body:JSON.stringify({title,speed:parameters.tempo,genre:parameters.genre,sounds:sounds.map(sound=>({sound_id:sound.soundId,category:sound.category}))})});
    if(guest&&!row.guest_token)throw new BackendCapabilityError('Guest generation credentials');
    return {id:row.id,status:row.status,guestToken:row.guest_token};
  },
  async getOutput(beatId,{guestToken,signal}={}){return toBeat(await apiRequest<BeatDto>(`/beats/${encodeURIComponent(beatId)}`,{signal},guestToken));},
  async claim(beatId,guestToken){return capability('Guest beat claiming',async()=>toBeat(await apiRequest<BeatDto>(`/beats/${encodeURIComponent(beatId)}/claim`,{method:'POST'},guestToken)));},
  async getDownloadUrl(beatId){return capability('Authenticated beat download',async()=>{const result=await apiRequest<{url:string}>(`/beats/${encodeURIComponent(beatId)}/download`);return absoluteUrl(result.url);});},
};

export function serviceErrorMessage(error:unknown){return error instanceof Error?error.message:'Something went wrong. Please try again.';}
