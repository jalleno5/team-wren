import { useEffect, useId, useRef, useState, type PointerEvent as ReactPointerEvent, type KeyboardEvent as ReactKeyboardEvent, type ReactNode } from 'react';
import { Link, NavLink, Navigate, Outlet, Route, Routes, useLocation, useNavigate } from 'react-router-dom';
import { ArrowDownToLine, ArrowLeft, ArrowRight, AudioLines, Beaker, Check, Flag, Globe2, Info, LockKeyhole, LogOut, Mic, Pause, Play, Plus, RotateCcw, Search, Settings2, Trash2, Upload, X } from 'lucide-react';
import { MIN_TEMPO, MAX_TEMPO, genres, soundCategories as categoryOptions, type SoundCategory, type SoundView } from './model';
import { outputPreview, sounds } from './fixtures';
import { ApiError, beatService, profileService, serviceErrorMessage, soundService, type BeatOutput } from './services';
import { useSession } from './session';
import { clipAudioBlob } from './audio';
function Logo({to='/library',compact=false}:{to?:string;compact?:boolean}){return <Link to={to} className={`brand-logo ${compact?'compact':''}`} aria-label="Encore — home"><span className="brand-wordmark-art" aria-hidden="true"/></Link>;}
function Wave({values}:{values:number[]}){
  const maximum=Math.max(...values,0.01);
  return <div className="wave" aria-hidden="true"><svg viewBox="0 0 240 64" preserveAspectRatio="none">{values.map((peak,i)=>{
    const height=8+Math.sqrt(peak/maximum)*46;
    return <rect key={i} x={i*10+1.5} y={(64-height)/2} width="7" height={height} rx="0" className="wave-pill"/>;
  })}</svg></div>;
}
function Modal({title,children,onClose}:{title:string;children:ReactNode;onClose:()=>void}) {
  const ref=useRef<HTMLDialogElement>(null); const titleId=useId();
  useEffect(()=>{const dialog=ref.current!;const old=document.activeElement as HTMLElement;dialog.showModal();return()=>{dialog.close();old?.focus();};},[]);
  return <dialog ref={ref} aria-labelledby={titleId} className="modal" onCancel={e=>{e.preventDefault();onClose();}} onClick={e=>{if(e.target===e.currentTarget)onClose();}}><div className="modal-heading"><h2 id={titleId}>{title}</h2><button className="icon-button" onClick={onClose} aria-label="Close dialog"><X size={20}/></button></div>{children}</dialog>;
}
function InfoTip({label,text}:{label:string;text:string}) {
  const id=useId();
  const trigger=useRef<HTMLButtonElement>(null);
  const [open,setOpen]=useState(false);
  const [position,setPosition]=useState({left:0,top:0});
  const show=()=>{
    const rect=trigger.current?.getBoundingClientRect();
    if(rect){setPosition({left:Math.max(12,Math.min(rect.left,window.innerWidth-272)),top:rect.bottom});setOpen(true);}
  };
  return <span className="info-tip" onMouseEnter={show} onMouseLeave={()=>setOpen(false)} onKeyDown={event=>{if(event.key==='Escape'){event.stopPropagation();setOpen(false);}}}>
    <button ref={trigger} type="button" className="info-trigger" aria-label={`About ${label}`} aria-describedby={open?id:undefined} onFocus={show} onBlur={()=>setOpen(false)} onClick={event=>{event.preventDefault();event.stopPropagation();show();}}><Info size={16}/></button>
    {open&&<span id={id} role="tooltip" className="info-tooltip" style={position}>{text}</span>}
  </span>;
}
function PageHeader({title,description,children}:{title:string;description:string;children?:ReactNode}){return <div className="page-heading"><div className="section-heading"><h1>{title}</h1><InfoTip label={title} text={description}/></div>{children&&<div className="heading-actions">{children}</div>}</div>;}

export default function App() {
  return <Routes>
    <Route path="/login" element={<Login/>}/>
    <Route element={<RequireAccess/>}><Route element={<Shell/>}>
      <Route path="/library" element={<LibraryPage/>}/>
      <Route path="/parameters" element={<RequireSounds><Parameters/></RequireSounds>}/>
      <Route path="/beat" element={<RequireGeneratedBeat><BeatEditor/></RequireGeneratedBeat>}/>
      <Route path="/profile" element={<RequireMember><Profile/></RequireMember>}/>
    </Route></Route>
    <Route path="*" element={<Navigate to="/login" replace/>}/>
  </Routes>;
}
function RequireAccess(){const {mode}=useSession();if(mode==='loading')return <main className="page"><p className="muted" role="status">Restoring your session…</p></main>;return mode==='signedOut'?<Navigate to="/login" replace/>:<Outlet/>;}
function RequireMember({children}:{children:ReactNode}){const {member}=useSession();return member?children:<Navigate to="/login" replace/>;}
function RequireSounds({children}:{children:ReactNode}){const {selectedSounds,soundCategories}=useSession();return selectedSounds.length&&selectedSounds.every(sound=>soundCategories[sound.id])?children:<Navigate to="/library" replace/>;}
function RequireGeneratedBeat({children}:{children:ReactNode}){const {generatedBeatId}=useSession();const {search}=useLocation();if(!generatedBeatId)return <Navigate to="/parameters" replace/>;const requested=new URLSearchParams(search).get('id');return requested===generatedBeatId?children:<Navigate to={`/beat?id=${encodeURIComponent(generatedBeatId)}`} replace/>;}
function Login() {
  const [status,setStatus]=useState<'idle'|'loading'|'error'>('idle');
  const [error,setError]=useState('');
  const navigate=useNavigate();
  const {search}=useLocation();
  const requestedReturn=new URLSearchParams(search).get('returnTo')||'/library';
  const {mode,signIn:beginSignIn,enterGuest,enterDevMember,consumeReturnTo}=useSession();
  useEffect(()=>{if(mode==='member')navigate(consumeReturnTo(),{replace:true});},[mode,navigate,consumeReturnTo]);
  const signIn=async()=>{setStatus('loading');setError('');try{await beginSignIn(requestedReturn.startsWith('/')?requestedReturn:'/library');}catch(reason){setError(serviceErrorMessage(reason));setStatus('error');}};
  const continueAsGuest=()=>{enterGuest();navigate('/library');};
  const continueAsTestUser=()=>{enterDevMember();navigate(requestedReturn.startsWith('/')?requestedReturn:'/library',{replace:true});};
  return <main className="login"><div className="login-brand"><Logo to="/login"/><h1>Build beats<br/>from everyday<br/><em>sounds.</em></h1></div>
    <div className="login-form"><div className="login-card"><h2>Sign in</h2>
      <button className="button google" onClick={signIn} disabled={status==='loading'}><span className="google-g">G</span>{status==='loading'?'Connecting…':'Continue with Google'}<ArrowRight size={18}/></button>
      <div className="login-divider"><span>or</span></div>
      <button className="button secondary guest-login" onClick={continueAsGuest}>Continue as guest<ArrowRight size={18}/></button>
      <p className="guest-note">Guests can build with community sounds. Private sounds, recording, reporting, Profile, and downloads require sign-in.</p>
      {import.meta.env.DEV&&<button className="button test-bypass" onClick={continueAsTestUser}><Beaker size={17}/>Bypass sign in for testing<span>Dev only</span></button>}
      {error&&<p className="service-message error" role="alert">{error}</p>}
    </div></div>
  </main>;
}
function Workflow() {
  const {pathname}=useLocation();
  const navigate=useNavigate();
  const {selectedSounds,soundCategories,classifyingSounds,generatedBeatId,prepareParameters}=useSession();
  if(pathname==='/profile')return null;
  const steps=[
    {path:'/library',name:'Sounds',enabled:true,disabledReason:''},
    {path:'/parameters',name:'Parameters',enabled:selectedSounds.length>0,disabledReason:'Select at least one sound first'},
    {path:generatedBeatId?`/beat?id=${encodeURIComponent(generatedBeatId)}`:'/beat',name:'Listen & export',enabled:Boolean(generatedBeatId),disabledReason:'Generate a beat first'},
  ];
  return <nav className="workflow" aria-label="Create a beat steps">{steps.map((step,index)=><div className="workflow-step" key={step.path}>
    <Link to={step.path} aria-current={pathname===new URL(step.path,window.location.origin).pathname?'step':undefined} aria-disabled={!step.enabled||index===1&&classifyingSounds} tabIndex={step.enabled&&!(index===1&&classifyingSounds)?undefined:-1} title={!step.enabled?step.disabledReason:undefined} onClick={async event=>{if(!step.enabled||index===1&&classifyingSounds){event.preventDefault();return;}if(index===1&&selectedSounds.some(sound=>!soundCategories[sound.id])){event.preventDefault();if(await prepareParameters())navigate('/parameters');}}} className={`${pathname===new URL(step.path,window.location.origin).pathname?'current':''} ${!step.enabled?'disabled':''}`.trim()}><span>{index+1}</span>{index===1&&classifyingSounds?'Classifying…':step.name}</Link>
    {index<2&&<ArrowRight size={28}/>}
  </div>)}</nav>;
}
function Shell() {
  const {pathname}=useLocation();
  const {guest}=useSession();
  return <div className="app-shell"><header className="app-header"><div className="app-header-inner"><Logo compact/>
    <nav className="app-nav" aria-label="Main navigation"><Link to="/library" className={pathname!=='/profile'?'active':''}><AudioLines size={19}/><span>Create a beat</span></Link>{guest?<Link to="/login"><span className="guest-avatar">G</span><span>Sign in</span></Link>:<NavLink to="/profile"><span className="avatar">AM</span><span>Profile</span></NavLink>}</nav>
  </div></header><div className="workspace"><Workflow/><Outlet/></div></div>;
}
function ActionDialog({title,onClose,children}:{title:string;onClose:()=>void;children?:ReactNode}) {
  return <Modal title={title} onClose={onClose}>{children}<div className="modal-actions"><button className="button secondary" onClick={onClose}>Cancel</button></div></Modal>;
}
function FlagDialog({sound,busy,error,onClose,onSubmit}:{sound:SoundView;busy:boolean;error:string;onClose:()=>void;onSubmit:(reason:string)=>Promise<void>}) {
  const [reason,setReason]=useState('');
  const [validationError,setValidationError]=useState('');
  const submit=async()=>{
    if(!reason){setValidationError('Choose a reason before flagging this sample.');return;}
    setValidationError('');
    await onSubmit(reason);
  };
  return <Modal title="Flag sample" onClose={onClose}>
    <div className="flag-dialog">
      <div className="flag-dialog-intro">
        <span className="flag-dialog-icon" aria-hidden="true"><Flag size={19}/></span>
        <div><p>Report <strong>“{sound.name}”</strong> for review.</p><p className="flag-dialog-note">A moderation report will be sent to the review team.</p></div>
      </div>
      <label className="form-label" htmlFor="flag-reason">Reason
        <select id="flag-reason" value={reason} aria-invalid={Boolean(validationError)} aria-describedby={validationError?'flag-reason-error':undefined} onChange={event=>{setReason(event.target.value);setValidationError('');}}>
          <option value="">Choose a reason</option>
          <option value="Inappropriate content">Inappropriate content</option>
          <option value="Copyright concern">Copyright concern</option>
          <option value="Spam or misleading">Spam or misleading</option>
        </select>
      </label>
      {validationError&&<p id="flag-reason-error" className="field-error" role="alert">{validationError}</p>}
      {error&&<p className="service-message error" role="alert">{error}</p>}
      <div className="modal-actions flag-dialog-actions"><button className="button secondary" disabled={busy} onClick={onClose}>Cancel</button><button className="button primary" disabled={busy} onClick={submit}>{busy?'Flagging…':'Flag sample'}</button></div>
    </div>
  </Modal>;
}
function SignInPrompt({message,onClose}:{message:string;onClose:()=>void}) {
  const location=useLocation();const returnTo=`${location.pathname}${location.search}`;
  return <Modal title="Sign in to continue" onClose={onClose}><p className="muted">{message}</p><div className="modal-actions"><button className="button secondary" onClick={onClose}>Not now</button><Link className="button primary" to={`/login?returnTo=${encodeURIComponent(returnTo)}`}>Go to sign in</Link></div></Modal>;
}

type RecordingPhase='idle'|'requesting'|'countdown'|'recording'|'review'|'saving'|'error';
function RecordDialog({onClose,onSaved}:{onClose:()=>void;onSaved:(sound:SoundView)=>void}) {
  const [phase,setPhase]=useState<RecordingPhase>('idle');
  const [countdown,setCountdown]=useState(3);
  const [recordingUrl,setRecordingUrl]=useState('');
  const [recordingBlob,setRecordingBlob]=useState<Blob|null>(null);
  const [title,setTitle]=useState('New recording');
  const [duration,setDuration]=useState(1.5);
  const [trimStart,setTrimStart]=useState(0);
  const [trimEnd,setTrimEnd]=useState(1.5);
  const [previewing,setPreviewing]=useState(false);
  const [error,setError]=useState('');
  const audioRef=useRef<HTMLAudioElement>(null);
  const trimTrackRef=useRef<HTMLDivElement>(null);
  const draggingRef=useRef<'start'|'end'|null>(null);
  const recorderRef=useRef<MediaRecorder|null>(null);
  const streamRef=useRef<MediaStream|null>(null);
  const timersRef=useRef<ReturnType<typeof setTimeout>[]>([]);

  const clearResources=()=>{
    timersRef.current.forEach(clearTimeout);
    timersRef.current=[];
    if(recorderRef.current?.state==='recording')recorderRef.current.stop();
    streamRef.current?.getTracks().forEach(track=>track.stop());
    streamRef.current=null;
    recorderRef.current=null;
  };
  const reset=()=>{
    clearResources();
    if(recordingUrl)URL.revokeObjectURL(recordingUrl);
    setRecordingUrl('');setRecordingBlob(null);setTitle('New recording');setDuration(1.5);setTrimStart(0);setTrimEnd(1.5);setPreviewing(false);setError('');setCountdown(3);setPhase('idle');
  };
  useEffect(()=>()=>{clearResources();if(recordingUrl)URL.revokeObjectURL(recordingUrl);},[recordingUrl]);

  const startCapture=async()=>{
    setError('');setPhase('requesting');
    try{
      if(!navigator.mediaDevices?.getUserMedia||typeof MediaRecorder==='undefined')throw new Error('Audio recording is not supported in this browser.');
      const stream=await navigator.mediaDevices.getUserMedia({audio:true});
      streamRef.current=stream;
      const recorder=new MediaRecorder(stream);
      recorderRef.current=recorder;
      const chunks:BlobPart[]=[];
      recorder.ondataavailable=event=>{if(event.data.size)chunks.push(event.data);};
      recorder.onerror=()=>{clearResources();setError('The recording could not be completed. Please try again.');setPhase('error');};
      recorder.onstop=()=>{
        stream.getTracks().forEach(track=>track.stop());
        streamRef.current=null;
        const blob=new Blob(chunks,{type:recorder.mimeType||'audio/webm'});
        if(!blob.size){setError('No audio was captured. Check your microphone and try again.');setPhase('error');return;}
        const url=URL.createObjectURL(blob);
        setRecordingBlob(blob);setRecordingUrl(url);setTrimStart(0);setTrimEnd(1.5);setPhase('review');
      };
      setPhase('countdown');setCountdown(3);
      [2,1].forEach((value,index)=>timersRef.current.push(setTimeout(()=>setCountdown(value),(index+1)*1000)));
      timersRef.current.push(setTimeout(()=>{
        recorder.start();setPhase('recording');
        timersRef.current.push(setTimeout(()=>{if(recorder.state==='recording')recorder.stop();},1500));
      },3000));
    }catch(reason){
      clearResources();
      const denied=reason instanceof DOMException&&(['NotAllowedError','SecurityError'].includes(reason.name));
      setError(denied?'Microphone access was denied. Allow access in your browser settings and try again.':serviceErrorMessage(reason));
      setPhase('error');
    }
  };
  const save=async()=>{
    if(!recordingBlob)return;
    if(!title.trim()){setError('Enter a name for this recording before saving.');return;}
    setPhase('saving');setError('');
    try{const clipped=await clipAudioBlob(recordingBlob,trimStart,trimEnd);const sound=await soundService.uploadRecording({name:title.trim(),blob:clipped.blob,trimStartSeconds:0,trimEndSeconds:clipped.durationSeconds});onSaved(sound);onClose();}
    catch(reason){setError(serviceErrorMessage(reason));setPhase('review');}
  };
  const previewSelection=async()=>{
    const audio=audioRef.current;if(!audio)return;
    if(!audio.paused){audio.pause();return;}
    audio.currentTime=trimStart;await audio.play();
  };
  const moveTrim=(kind:'start'|'end',value:number)=>{
    const clamped=Math.max(0,Math.min(duration,value));
    if(kind==='start')setTrimStart(Math.min(clamped,trimEnd-.05));
    else setTrimEnd(Math.max(clamped,trimStart+.05));
  };
  const dragTrim=(event:ReactPointerEvent<HTMLDivElement>)=>{
    const kind=draggingRef.current;const track=trimTrackRef.current;if(!kind||!track)return;
    const rect=track.getBoundingClientRect();moveTrim(kind,(event.clientX-rect.left)/rect.width*duration);
  };
  const beginTrimDrag=(kind:'start'|'end',event:ReactPointerEvent<HTMLButtonElement>)=>{
    draggingRef.current=kind;event.currentTarget.setPointerCapture(event.pointerId);event.preventDefault();
  };
  const trimKey=(kind:'start'|'end',event:ReactKeyboardEvent<HTMLButtonElement>)=>{
    const direction=event.key==='ArrowLeft'?-1:event.key==='ArrowRight'?1:0;if(!direction)return;
    event.preventDefault();moveTrim(kind,(kind==='start'?trimStart:trimEnd)+direction*.01);
  };
  const formatTrim=(value:number)=>`${value.toFixed(2)}s`;
  const close=()=>{clearResources();onClose();};

  return <Modal title="Record sound" onClose={close}>
    <div className="capture-zone" aria-live="polite">
      {phase==='idle'&&<><button className="record-circle" onClick={startCapture} aria-label="Start three second countdown"><Mic size={30}/></button><strong>Ready to record?</strong><span>You’ll get a 3-second countdown. Maximum duration: 1.5 seconds.</span></>}
      {phase==='requesting'&&<><Mic size={34}/><strong>Waiting for microphone…</strong><span>Approve access in your browser to begin the countdown.</span></>}
      {phase==='countdown'&&<><strong className="countdown-number">{countdown}</strong><span>Get your sound ready</span></>}
      {phase==='recording'&&<><span className="recording-pulse"/><strong>Recording…</strong><span>Capturing 1.5 seconds</span></>}
      {phase==='review'&&recordingUrl&&<><strong>Drag the waveform edges to trim</strong><label className="form-label recording-title">Recording name<input value={title} maxLength={80} onChange={event=>setTitle(event.target.value)} /></label><audio ref={audioRef} className="visually-hidden" src={recordingUrl} preload="metadata" onLoadedMetadata={event=>{const next=Number.isFinite(event.currentTarget.duration)?event.currentTarget.duration:1.5;setDuration(next);setTrimEnd(next);}} onPlay={()=>setPreviewing(true)} onPause={()=>setPreviewing(false)} onEnded={()=>setPreviewing(false)} onTimeUpdate={event=>{if(event.currentTarget.currentTime>=trimEnd)event.currentTarget.pause();}}/><div className="trim-editor">
        <div ref={trimTrackRef} className="trim-track" onPointerMove={dragTrim} onPointerUp={()=>{draggingRef.current=null;}} onPointerCancel={()=>{draggingRef.current=null;}}>
          <div className="trim-waveform-bars" aria-hidden="true">{outputPreview.waveform.slice(0,36).map((value,index)=><span key={index} style={{height:`${24+value*70}%`}}/>)}</div>
          <div className="trim-selection" style={{left:`${duration?trimStart/duration*100:0}%`,width:`${duration?(trimEnd-trimStart)/duration*100:100}%`}} aria-hidden="true"/>
          <button type="button" className="trim-handle trim-handle-start" style={{left:`${duration?trimStart/duration*100:0}%`}} role="slider" aria-label="Sample start" aria-valuemin={0} aria-valuemax={trimEnd} aria-valuenow={trimStart} aria-valuetext={formatTrim(trimStart)} onPointerDown={event=>beginTrimDrag('start',event)} onKeyDown={event=>trimKey('start',event)}/>
          <button type="button" className="trim-handle trim-handle-end" style={{left:`${duration?trimEnd/duration*100:100}%`}} role="slider" aria-label="Sample stop" aria-valuemin={trimStart} aria-valuemax={duration} aria-valuenow={trimEnd} aria-valuetext={formatTrim(trimEnd)} onPointerDown={event=>beginTrimDrag('end',event)} onKeyDown={event=>trimKey('end',event)}/>
        </div>
        <div className="trim-values"><span>Start <output>{formatTrim(trimStart)}</output></span><span>Stop <output>{formatTrim(trimEnd)}</output></span></div>
        <div className="trim-summary"><span>Saved length</span><strong>{formatTrim(trimEnd-trimStart)}</strong></div>
      </div><button className="button secondary preview-trim" onClick={previewSelection}>{previewing?<Pause size={16}/>:<Play size={16}/>} {previewing?'Pause preview':'Preview selection'}</button><span>Only the selected audio will be clipped and uploaded.</span></>}
      {phase==='saving'&&<><strong>Saving recording…</strong><span>Sending your sound to the library service.</span></>}
      {phase==='error'&&<><strong>Recording unavailable</strong><span>{error}</span></>}
    </div>
    {error&&phase==='review'&&<p className="service-message error" role="alert">{error}</p>}
    <div className="modal-actions">
      {(phase==='error'||phase==='review')&&<button className="button secondary" onClick={reset}><RotateCcw size={16}/>Try again</button>}
      {phase==='review'&&<button className="button primary" onClick={save}>Save sound</button>}
      <button className="button secondary" onClick={close}>Cancel</button>
    </div>
  </Modal>;
}

function LibraryPage() {
  const {guest,selectedSounds,toggleSound,removeSound,classifyingSounds,classificationError,prepareParameters}=useSession();
  const navigate=useNavigate();
  const [tab,setTab]=useState<'mine'|'public'>(guest?'public':'mine');
  const [signInPrompt,setSignInPrompt]=useState('');
  const [query,setQuery]=useState('');
  const [librarySounds,setLibrarySounds]=useState<SoundView[]>(sounds);
  const [dialog,setDialog]=useState<{type:string;sound?:SoundView}|null>(null);
  const [serviceError,setServiceError]=useState('');
  const [busy,setBusy]=useState('');
  const [flaggedIds,setFlaggedIds]=useState<string[]>([]);
  const shown=librarySounds.filter(sound=>(tab==='mine'?sound.owned:sound.visibility==='public')&&sound.name.toLowerCase().includes(query.toLowerCase()));
  const run=async(label:string,operation:()=>Promise<unknown>)=>{setBusy(label);setServiceError('');try{await operation();return true;}catch(reason){setServiceError(serviceErrorMessage(reason));return false;}finally{setBusy('');}};
  useEffect(()=>{const controller=new AbortController();soundService.list({scope:tab,query,signal:controller.signal}).then(rows=>{setLibrarySounds(rows);setServiceError('');}).catch(reason=>{if(reason instanceof DOMException&&reason.name==='AbortError')return;setLibrarySounds(sounds);setServiceError(serviceErrorMessage(reason));});return()=>controller.abort();},[tab,query]);
  const previewSound=async(sound:SoundView)=>{
    const playback=await soundService.getPlayback(sound.id);
    const audio=new Audio(playback.url);
    await new Promise<void>((resolve,reject)=>{audio.addEventListener('loadedmetadata',()=>resolve(),{once:true});audio.addEventListener('error',()=>reject(new Error('The sample could not be loaded.')),{once:true});});
    audio.currentTime=playback.trimStartSeconds;
    audio.addEventListener('timeupdate',()=>{if(playback.trimEndSeconds!==undefined&&audio.currentTime>=playback.trimEndSeconds)audio.pause();});
    await audio.play();
  };
  const openPrivateLibrary=()=>{if(guest){setSignInPrompt('Guest mode includes community sounds only. Sign in to access your private sound library.');return;}setTab('mine');};
  const openRecorder=()=>{if(guest){setSignInPrompt('Sign in to record and save your own sounds.');return;}setServiceError('');setDialog({type:'Record sound'});};
  return <main className="page library-page">
    <PageHeader title="Select your sounds" description="Record sounds up to 1.5 seconds and select samples for your beat.">{guest&&<span className="guest-mode-badge">Guest mode · public sounds only</span>}</PageHeader>
    <div className="library-layout"><section className="sound-library">
      <div className="library-controls"><div className="library-tab-actions">
        <div className="library-tabs" role="tablist" aria-label="Sound library" onKeyDown={e=>{if(e.key==='ArrowLeft'||e.key==='ArrowRight'){e.preventDefault();const next=tab==='mine'?'public':'mine';if(next==='mine')openPrivateLibrary();else setTab('public');e.currentTarget.querySelectorAll<HTMLButtonElement>('button')[tab==='mine'?1:0]?.focus();}}}>
          <button role="tab" aria-selected={tab==='mine'} className={tab==='mine'?'active':''} onClick={openPrivateLibrary}><LockKeyhole size={16}/>My sounds<span>{tab==='mine'?shown.length:sounds.filter(s=>s.owned).length}</span></button>
          <button role="tab" aria-selected={tab==='public'} className={tab==='public'?'active':''} onClick={()=>setTab('public')}><Globe2 size={16}/>Community<span>{tab==='public'?shown.length:sounds.filter(s=>s.visibility==='public').length}</span></button>
        </div>
        <button className="button primary record-action" onClick={openRecorder}><Mic size={21}/>Record a sound</button>
      </div><div className="library-tools"><label className="search"><Search size={17}/><input aria-label="Search sounds" placeholder="Find a sound…" value={query} onChange={event=>setQuery(event.target.value)}/></label></div></div>
      <div className="sound-grid">{shown.map(sound=><article key={sound.id} className={`sound-card ${sound.owned&&!guest?'owned-sound':''} visibility-${sound.visibility} ${selectedSounds.some(s=>s.id===sound.id)?'selected':''}`}>
        <div className="sound-card-top">{sound.owned&&!guest?<button className="delete-sound-button" aria-label={`Delete ${sound.name}`} onClick={()=>{setServiceError('');setDialog({type:'Delete sound',sound});}}><Trash2 size={15}/>Delete</button>:<button className={`flag-sound-button ${flaggedIds.includes(sound.id)?'flagged':''}`} aria-label={`Flag ${sound.name}`} disabled={flaggedIds.includes(sound.id)} onClick={()=>{if(guest){setSignInPrompt('Sign in before reporting a community sample.');return;}setServiceError('');setDialog({type:'Flag sample',sound});}}><Flag size={15}/>{flaggedIds.includes(sound.id)?'Flagged':'Flag'}</button>}</div>
        <div className="sound-name"><h3>{sound.name}</h3><span className="visibility-badge">{sound.visibility==='public'?<Globe2 size={12}/>:<LockKeyhole size={12}/>} {sound.visibility==='public'?'Public':'Private'}</span></div>
        <div className="sound-preview"><button className="preview-button" aria-label={`Preview ${sound.name}`} disabled={busy===`preview-${sound.id}`} onClick={()=>run(`preview-${sound.id}`,()=>previewSound(sound))}><Play size={17} fill="currentColor"/></button><Wave values={sound.waveform}/></div>
        <div className="sound-card-bottom">{sound.owned&&!guest?<button className="add-button publish-button" disabled={busy===`visibility-${sound.id}`} onClick={async()=>{const next=sound.visibility==='private'?'public':'private';if(await run(`visibility-${sound.id}`,async()=>{const updated=await soundService.setVisibility(sound.id,next);setLibrarySounds(current=>current.map(item=>item.id===updated.id?updated:item));}))setDialog(null);}}>{sound.visibility==='private'?<Globe2 size={14}/>:<LockKeyhole size={14}/>}Make {sound.visibility==='private'?'public':'private'}</button>:<span>by {sound.creator}</span>}
          <button className={`add-button ${selectedSounds.some(item=>item.id===sound.id)?'added':''}`} aria-pressed={selectedSounds.some(item=>item.id===sound.id)} disabled={!selectedSounds.some(item=>item.id===sound.id)&&selectedSounds.length>=4} onClick={()=>{if(!toggleSound(sound))setServiceError('You can select up to four sounds for a beat.');}}>{selectedSounds.some(item=>item.id===sound.id)?<><Check size={14}/>Added</>:<><Plus size={14}/>Add to beat</>}</button>
        </div>
      </article>)}</div>
      {serviceError&&<p className="service-message error" role="alert">{serviceError}</p>}
    </section><aside className="beat-tray"><div className="mobile-tray-title"><div className="tray-heading"><h3>Selected sounds</h3><span className="count">{selectedSounds.length}</span></div></div>
      <div className="tray-sounds">{selectedSounds.map((sound,index)=><div className="tray-sound" key={sound.id}><span className="track-number">{String(index+1).padStart(2,'0')}</span><div><strong>{sound.name}</strong></div><button className="icon-button" aria-label={`Remove ${sound.name}`} onClick={()=>removeSound(sound.id)}><X size={14}/></button></div>)}</div>
      {selectedSounds.length?<button className="button primary full continue-action" disabled={classifyingSounds} onClick={async()=>{if(await prepareParameters())navigate('/parameters');}}>{classifyingSounds?'Classifying sounds…':<>Continue to parameters<ArrowRight size={21}/></>}</button>:<button className="button primary full continue-action" disabled aria-label="Select at least one sound to continue">Select a sound to continue</button>}
      {classificationError&&<p className="service-message error" role="alert">{classificationError}</p>}
    </aside></div>
    {dialog?.type==='Record sound'&&<RecordDialog onClose={()=>setDialog(null)} onSaved={sound=>setLibrarySounds(current=>[sound,...current])}/>}
    {dialog?.type==='Delete sound'&&<ActionDialog title={dialog.type} onClose={()=>setDialog(null)}>
      {dialog.type==='Delete sound'&&<><p className="muted">Delete “{dialog.sound?.name}”?</p><button className="button secondary" disabled={busy==='delete'} onClick={async()=>{if(dialog.sound&&await run('delete',()=>soundService.delete(dialog.sound!.id))){setLibrarySounds(current=>current.filter(sound=>sound.id!==dialog.sound!.id));setDialog(null);}}}>Delete sound</button></>}
      {serviceError&&<p className="service-message error" role="alert">{serviceError}</p>}
    </ActionDialog>}
    {dialog?.type==='Flag sample'&&dialog.sound&&<FlagDialog
      sound={dialog.sound}
      busy={busy==='flag'}
      error={serviceError}
      onClose={()=>setDialog(null)}
      onSubmit={async reason=>{if(await run('flag',()=>soundService.flag(dialog.sound!.id,reason))){setFlaggedIds(current=>[...current,dialog.sound!.id]);setDialog(null);}}}
    />}
    {signInPrompt&&<SignInPrompt message={signInPrompt} onClose={()=>setSignInPrompt('')}/>}
  </main>;
}
function SelectField({label,value,options,onChange}:{label:string;value:string;options:readonly string[];onChange?:(value:string)=>void}) {
  return <label className="form-label">{label}<select value={value} onChange={event=>onChange?.(event.target.value)}>{options.map(option=><option key={option} value={option}>{option[0].toUpperCase()+option.slice(1)}</option>)}</select></label>;
}
function Parameters() {
  const {guest,selectedSounds,soundCategories,setSoundCategory,setPendingGuestBeat,setGeneratedBeatId}=useSession();
  const [tempo,setTempo]=useState(120);
  const [genre,setGenre]=useState('electronic');
  const [generating,setGenerating]=useState(false);
  const [error,setError]=useState('');
  const navigate=useNavigate();
  const generate=async()=>{
    if(!selectedSounds.length){setError('Select at least one sound before generating a beat.');return;}
    setGenerating(true);setError('');
    try{
      const beat=await beatService.generate({sounds:selectedSounds.map(sound=>({soundId:sound.id,category:soundCategories[sound.id]})),parameters:{tempo,genre},guest});
      if(guest&&beat.guestToken)setPendingGuestBeat({id:beat.id,token:beat.guestToken});
      setGeneratedBeatId(beat.id);
      navigate(`/beat?id=${encodeURIComponent(beat.id)}`);
    }catch(reason){setError(serviceErrorMessage(reason));}finally{setGenerating(false);}
  };
  return <main className="page"><PageHeader title="Set beat parameters" description="Choose the tempo and style sent to the beat generator."/>
    <div className="parameters-layout"><section className="panel parameter-panel">
      <div className="tempo-heading"><label htmlFor="tempo">Tempo</label><div><output htmlFor="tempo" className="tempo-value">{tempo}</output><span>BPM</span></div></div>
      <input id="tempo" aria-label="Tempo" type="range" min={MIN_TEMPO} max={MAX_TEMPO} value={tempo} onChange={event=>setTempo(Number(event.target.value))}/>
      <div className="range-labels"><span>{MIN_TEMPO} BPM</span><span>{MAX_TEMPO} BPM</span></div>
      <SelectField label="Style / genre" value={genre} options={genres} onChange={setGenre}/>
      <fieldset className="sound-category-list"><legend>Sound categories</legend><p className="muted">Adjust how each sound is used in this beat.</p>{selectedSounds.map(sound=><SelectField key={sound.id} label={sound.name} value={soundCategories[sound.id]} options={categoryOptions} onChange={value=>setSoundCategory(sound.id,value as SoundCategory)}/>)}</fieldset>
    </section><aside className="panel session-summary"><h2>Your settings</h2>{[['Sounds',String(selectedSounds.length)],['Tempo',`${tempo} BPM`],['Style',genre]].map(([label,value])=><div className="summary-row" key={label}><span>{label}</span><strong>{value}</strong></div>)}
      <button className="button primary full" onClick={generate} disabled={generating||!selectedSounds.length}>{generating?'Generating…':'Generate beat'}</button>{error&&<p className="service-message error" role="alert">{error}</p>}<Link className="back-link" to="/library"><ArrowLeft size={14}/>Back to sounds</Link>
    </aside></div>
  </main>;
}
function BeatEditor() {
  const {guest,member,pendingGuestBeat,setPendingGuestBeat}=useSession();
  const [signInPrompt,setSignInPrompt]=useState(false);
  const {search}=useLocation();
  const beatId=new URLSearchParams(search).get('id')??'';
  const [output,setOutput]=useState<BeatOutput|null>(null);
  const [error,setError]=useState('');
  const [loading,setLoading]=useState(true);
  const [playing,setPlaying]=useState(false);
  const [time,setTime]=useState(0);
  const audioRef=useRef<HTMLAudioElement>(null);
  useEffect(()=>{
    const controller=new AbortController();let timer:ReturnType<typeof setTimeout>|undefined;
    const wait=()=>new Promise<void>(resolve=>{timer=setTimeout(resolve,1000);});
    const load=async()=>{
      setLoading(true);setError('');
      if(!beatId){setError('Generate a beat before opening the output page.');setLoading(false);return;}
      let guestToken=pendingGuestBeat?.id===beatId?pendingGuestBeat.token:undefined;
      if(guest&&!guestToken){setError('Guest generation credentials are not available from the current backend.');setLoading(false);return;}
      try{
        if(member&&guestToken){
          const claimed=await beatService.claim(beatId,guestToken);if(controller.signal.aborted)return;setPendingGuestBeat(null);guestToken=undefined;setOutput(claimed);
        }
        const deadline=Date.now()+30*60*1000;
        while(!controller.signal.aborted&&Date.now()<deadline){
          let result:BeatOutput;
          try{result=await beatService.getOutput(beatId,{guestToken,signal:controller.signal});}
          catch(reason){if(reason instanceof ApiError&&[0,502,503,504].includes(reason.status)){await wait();continue;}throw reason;}
          if(controller.signal.aborted)return;setOutput(result);
          if(result.status==='completed'){if(!result.audioUrl)setError('Beat generation completed, but the backend did not provide playable audio.');setLoading(false);return;}
          if(result.status==='failed'){setError(result.error||'Beat generation failed. Please try again.');setLoading(false);return;}
          await wait();
        }
        if(!controller.signal.aborted){setError('This beat is taking longer than expected. Reopen this page later to check its progress.');setLoading(false);}
      }catch(reason){if(!controller.signal.aborted){setError(serviceErrorMessage(reason));setLoading(false);}}
    };
    load();return()=>{controller.abort();if(timer)clearTimeout(timer);};
  },[beatId,guest,member,pendingGuestBeat]);
  const duration=output?.durationSeconds||outputPreview.durationSeconds;
  const values=output?.waveform??outputPreview.waveform;
  const togglePlayback=async()=>{const audio=audioRef.current;if(!audio||!output?.audioUrl)return;if(audio.paused)await audio.play();else audio.pause();};
  const seek=(value:number)=>{const audio=audioRef.current;setTime(value);if(audio)audio.currentTime=value;};
  const download=async()=>{
    if(guest){setSignInPrompt(true);return;}
    if(!output)return;
    setError('');
    try{const url=await beatService.getDownloadUrl(output.id);window.location.assign(url);}catch(reason){setError(serviceErrorMessage(reason));}
  };
  const format=(seconds:number)=>`${Math.floor(seconds/60)}:${Math.floor(seconds%60).toString().padStart(2,'0')}`;
  const unavailable=!output?.audioUrl;
  return <main className="page output-page"><PageHeader title="Your beat" description="Listen to your generated audio and download the WAV."><Link className="button secondary" to="/parameters"><Settings2 size={16}/>Parameters</Link></PageHeader>
    <section className="audio-output-card" aria-busy={loading}>
      <div className="audio-output-heading"><div><span className="eyebrow">Generated output</span><h2>{output?.name??outputPreview.name}</h2></div><button className="button primary" onClick={download} disabled={!guest&&(!output||loading||output.status!=='completed')}><ArrowDownToLine size={17}/>{guest?'Sign in to export':'Download WAV'}</button></div>
      <div className="output-waveform" aria-label="Audio waveform visualization">{values.map((value,index)=><span key={index} style={{height:`${18+value*78}%`}} className={index/values.length<time/duration?'played':''}/>)}</div>
      <div className="audio-controls">
        <button className="transport-play" onClick={togglePlayback} disabled={unavailable} aria-label={playing?'Pause beat':'Play beat'}>{playing?<Pause size={22} fill="currentColor"/>:<Play size={22} fill="currentColor"/>}</button>
        <span className="audio-time">{format(time)}</span>
        <input aria-label="Beat playback position" type="range" min={0} max={duration} step={0.01} value={Math.min(time,duration)} disabled={unavailable} onChange={event=>seek(Number(event.target.value))}/>
        <span className="audio-time">{format(duration)}</span>
      </div>
      {output?.audioUrl&&<audio
        ref={audioRef}
        src={output.audioUrl}
        onPlay={()=>setPlaying(true)}
        onPause={()=>setPlaying(false)}
        onTimeUpdate={event=>setTime(event.currentTarget.currentTime)}
        onEnded={()=>setPlaying(false)}
        onError={()=>setError('The generated audio file could not be loaded.')}
      />}
      {error&&<p className="service-message error" role="alert">{error}</p>}
      {loading&&<p className="output-empty" role="status">{output?.status==='processing'?'Processing your beat…':'Waiting for the beat generator…'}</p>}
      {!loading&&unavailable&&!error&&<p className="output-empty">The player will activate when the beat output API returns an audio file.</p>}
    </section>
    <Link className="back-link" to="/library"><ArrowLeft size={15}/>Back to sounds</Link>
    {signInPrompt&&<SignInPrompt message="Guest mode can listen to generated beats, but export requires an account." onClose={()=>setSignInPrompt(false)}/>}
  </main>;
}
function Profile() {
  const {signOut}=useSession();
  const navigate=useNavigate();
  const [username,setUsername]=useState('Alex Morgan');
  const [email,setEmail]=useState('alex.morgan@example.com');
  const [busy,setBusy]=useState('');
  const [error,setError]=useState('');
  const photoInput=useRef<HTMLInputElement>(null);
  const run=async(label:string,operation:()=>Promise<unknown>)=>{setBusy(label);setError('');try{await operation();}catch(reason){setError(serviceErrorMessage(reason));}finally{setBusy('');}};
  useEffect(()=>{let current=true;profileService.get().then(profile=>{if(current){setUsername(profile.username);setEmail(profile.email);}}).catch(reason=>{if(current)setError(serviceErrorMessage(reason));});return()=>{current=false;};},[]);
  return <main className="page"><PageHeader title="Profile" description="Manage your profile and account settings."/><section className="panel profile-panel">
    <div className="profile-avatar"><span className="avatar">AM</span><div><div className="section-heading profile-photo-heading"><strong>Your photo</strong><InfoTip label="profile photo" text="Choose a photo for your profile."/></div><input ref={photoInput} className="visually-hidden" type="file" accept="image/*" onChange={event=>{const file=event.target.files?.[0];if(file)run('photo',()=>profileService.uploadPhoto(file));}}/><button className="button secondary" disabled={busy==='photo'} onClick={()=>photoInput.current?.click()}><Upload size={15}/>{busy==='photo'?'Uploading…':'Change photo'}</button></div></div>
    <div className="form-stack"><label>Username<input value={username} onChange={event=>setUsername(event.target.value)}/></label><label>Email address<input value={email} readOnly aria-readonly="true"/><span className="field-help">Email is managed by your Google account.</span></label>
      <div className="account-help"><LockKeyhole size={20}/><div><strong>Password & account security</strong><p>Manage your password through Google.</p></div></div>
      <button className="button primary" disabled={busy==='save'||!username.trim()} onClick={()=>run('save',()=>profileService.update({username:username.trim()}))}>{busy==='save'?'Saving…':'Save changes'}</button>
      {error&&<p className="service-message error" role="alert">{error}</p>}
    </div><div className="profile-signout"><button className="button secondary" disabled={busy==='signout'} onClick={()=>run('signout',async()=>{await signOut();navigate('/login',{replace:true});})}><LogOut size={16}/>{busy==='signout'?'Signing out…':'Sign out'}</button></div>
  </section></main>;
}
