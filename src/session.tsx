import { createContext, useContext, useEffect, useMemo, useState, type ReactNode } from 'react';
import { supabase } from './lib/supabase';
import { isSoundCategory, type SoundCategory, type SoundView } from './model';
import { ServiceNotConfiguredError, serviceErrorMessage, setAccessTokenProvider, soundService } from './services';

type AccessMode='loading'|'signedOut'|'guest'|'member'|'devMember';
interface PendingGuestBeat { id:string; token:string }
interface SessionContextValue {
  mode:AccessMode;
  guest:boolean;
  member:boolean;
  selectedSounds:SoundView[];
  soundCategories:Record<string,SoundCategory>;
  classifyingSounds:boolean;
  classificationError:string;
  pendingGuestBeat:PendingGuestBeat|null;
  generatedBeatId:string|null;
  enterGuest():void;
  enterDevMember():void;
  signIn(returnTo:string):Promise<void>;
  signOut():Promise<void>;
  toggleSound(sound:SoundView):boolean;
  removeSound(id:string):void;
  setSoundCategory(soundId:string,category:SoundCategory):void;
  prepareParameters():Promise<boolean>;
  setPendingGuestBeat(value:PendingGuestBeat|null):void;
  setGeneratedBeatId(value:string|null):void;
  consumeReturnTo():string;
}

const ACCESS_KEY='encore-access-mode';
const SOUNDS_KEY='encore-selected-sounds';
const CATEGORIES_KEY='encore-sound-categories';
const PENDING_BEAT_KEY='encore-pending-guest-beat';
const GENERATED_BEAT_KEY='encore-generated-beat-id';
const RETURN_TO_KEY='encore-post-login-return';

function readSelected():SoundView[]{
  try{const value=JSON.parse(sessionStorage.getItem(SOUNDS_KEY)??'[]');return Array.isArray(value)?value.filter(item=>item&&typeof item.id==='string').slice(0,4):[];}catch{return [];}
}
function readCategories():Record<string,SoundCategory>{
  try{const value=JSON.parse(sessionStorage.getItem(CATEGORIES_KEY)??'{}');if(!value||typeof value!=='object'||Array.isArray(value))return {};return Object.fromEntries(Object.entries(value).filter((entry):entry is [string,SoundCategory]=>isSoundCategory(entry[1])));}catch{return {};}
}
function readPending():PendingGuestBeat|null{
  try{const value=JSON.parse(sessionStorage.getItem(PENDING_BEAT_KEY)??'null');return value&&typeof value.id==='string'&&typeof value.token==='string'?value:null;}catch{return null;}
}

const SessionContext=createContext<SessionContextValue|null>(null);

export function SessionProvider({children}:{children:ReactNode}){
  const [mode,setMode]=useState<AccessMode>('loading');
  const [selectedSounds,setSelectedSounds]=useState<SoundView[]>(readSelected);
  const [soundCategories,setCategoriesState]=useState<Record<string,SoundCategory>>(readCategories);
  const [classifyingSounds,setClassifyingSounds]=useState(false);
  const [classificationError,setClassificationError]=useState('');
  const [pendingGuestBeat,setPendingBeatState]=useState<PendingGuestBeat|null>(readPending);
  const [generatedBeatId,setGeneratedBeatState]=useState<string|null>(()=>sessionStorage.getItem(GENERATED_BEAT_KEY));

  useEffect(()=>{
    let active=true;
    if(!supabase){
      const stored=sessionStorage.getItem(ACCESS_KEY);
      setMode(stored==='guest'?'guest':stored==='dev-member'?'devMember':'signedOut');
      return;
    }
    supabase.auth.getSession().then(({data})=>{if(!active)return;if(data.session){sessionStorage.setItem(ACCESS_KEY,'member');setMode('member');}else{setMode(sessionStorage.getItem(ACCESS_KEY)==='guest'?'guest':'signedOut');}});
    const {data}=supabase.auth.onAuthStateChange((_event,session)=>{if(!active)return;if(session){sessionStorage.setItem(ACCESS_KEY,'member');setMode('member');}else if(sessionStorage.getItem(ACCESS_KEY)!=='guest'){sessionStorage.removeItem(ACCESS_KEY);setMode('signedOut');}});
    return()=>{active=false;data.subscription.unsubscribe();};
  },[]);

  useEffect(()=>{setAccessTokenProvider(async()=>{if(mode==='devMember'||!supabase)return undefined;return (await supabase.auth.getSession()).data.session?.access_token;});},[mode]);
  useEffect(()=>{sessionStorage.setItem(SOUNDS_KEY,JSON.stringify(selectedSounds));},[selectedSounds]);
  useEffect(()=>{sessionStorage.setItem(CATEGORIES_KEY,JSON.stringify(soundCategories));},[soundCategories]);

  const setPendingGuestBeat=(value:PendingGuestBeat|null)=>{setPendingBeatState(value);if(value)sessionStorage.setItem(PENDING_BEAT_KEY,JSON.stringify(value));else sessionStorage.removeItem(PENDING_BEAT_KEY);};
  const updateGeneratedBeatId=(value:string|null)=>{setGeneratedBeatState(value);if(value)sessionStorage.setItem(GENERATED_BEAT_KEY,value);else sessionStorage.removeItem(GENERATED_BEAT_KEY);};
  const invalidateGeneratedBeat=()=>{updateGeneratedBeatId(null);setPendingGuestBeat(null);};
  const value=useMemo<SessionContextValue>(()=>({
    mode,guest:mode==='guest',member:mode==='member'||mode==='devMember',selectedSounds,soundCategories,classifyingSounds,classificationError,pendingGuestBeat,generatedBeatId,
    enterGuest(){sessionStorage.setItem(ACCESS_KEY,'guest');setMode('guest');setSelectedSounds([]);setCategoriesState({});invalidateGeneratedBeat();},
    enterDevMember(){sessionStorage.setItem(ACCESS_KEY,'dev-member');setMode('devMember');},
    async signIn(returnTo){if(!supabase)throw new ServiceNotConfiguredError('Supabase Google sign-in');sessionStorage.setItem(RETURN_TO_KEY,returnTo);const {error}=await supabase.auth.signInWithOAuth({provider:'google',options:{redirectTo:`${window.location.origin}/login`}});if(error)throw error;},
    async signOut(){if(supabase&&mode==='member'){const {error}=await supabase.auth.signOut();if(error)throw error;}sessionStorage.removeItem(ACCESS_KEY);sessionStorage.removeItem(SOUNDS_KEY);sessionStorage.removeItem(CATEGORIES_KEY);setSelectedSounds([]);setCategoriesState({});invalidateGeneratedBeat();setMode('signedOut');},
    toggleSound(sound){setClassificationError('');if(selectedSounds.some(item=>item.id===sound.id)){setSelectedSounds(current=>current.filter(item=>item.id!==sound.id));setCategoriesState(current=>{const next={...current};delete next[sound.id];return next;});invalidateGeneratedBeat();return true;}if(selectedSounds.length>=4)return false;setSelectedSounds(current=>[...current,sound]);invalidateGeneratedBeat();return true;},
    removeSound(id){setClassificationError('');setSelectedSounds(current=>current.filter(item=>item.id!==id));setCategoriesState(current=>{const next={...current};delete next[id];return next;});invalidateGeneratedBeat();},
    setSoundCategory(soundId,category){setCategoriesState(current=>({...current,[soundId]:category}));invalidateGeneratedBeat();},
    async prepareParameters(){const missing=selectedSounds.filter(sound=>!soundCategories[sound.id]);if(!missing.length){setClassificationError('');return true;}setClassifyingSounds(true);setClassificationError('');try{const classified=await Promise.all(missing.map(async sound=>[sound.id,await soundService.classify(sound.id)] as const));setCategoriesState(current=>({...current,...Object.fromEntries(classified)}));return true;}catch(reason){setClassificationError(serviceErrorMessage(reason));return false;}finally{setClassifyingSounds(false);}},
    setPendingGuestBeat,
    setGeneratedBeatId:updateGeneratedBeatId,
    consumeReturnTo(){const route=sessionStorage.getItem(RETURN_TO_KEY)||'/library';sessionStorage.removeItem(RETURN_TO_KEY);return route.startsWith('/')?route:'/library';},
  }),[classificationError,classifyingSounds,generatedBeatId,mode,pendingGuestBeat,selectedSounds,soundCategories]);
  return <SessionContext.Provider value={value}>{children}</SessionContext.Provider>;
}

export function useSession(){const value=useContext(SessionContext);if(!value)throw new Error('useSession must be used within SessionProvider');return value;}
