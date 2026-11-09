import { useEffect, useId, useRef, useState, type ReactNode } from 'react';
import { Link, NavLink, Navigate, Outlet, Route, Routes, useLocation, useNavigate } from 'react-router-dom';
import { ArrowDownToLine, ArrowLeft, ArrowRight, AudioLines, Check, ChevronDown, Flag, Globe2, Info, LockKeyhole, LogOut, Mic, Pause, Play, Plus, RotateCcw, Search, Settings2, Trash2, Upload, X } from 'lucide-react';
import { MIN_TEMPO, MAX_TEMPO, ensembles, genres, gmNames, modes, type SoundView } from './model';
import { outputPreview, sounds, selectedSounds } from './fixtures';
import { authService, beatService, profileService, serviceErrorMessage, soundService, type BeatOutput } from './services';
function Logo(){return <Link to="/library" className="brand-placeholder" aria-label="Logo placeholder — home"><svg viewBox="0 0 32 32" aria-hidden="true"><rect x="2" y="2" width="28" height="28" fill="none" stroke="currentColor" strokeWidth="1.5" strokeDasharray="3 3"/><path d="m9 9 14 14M23 9 9 23" fill="none" stroke="currentColor" strokeWidth="1.5"/></svg><span>LOGO</span></Link>;}
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
    <Route element={<Shell/>}>
      <Route path="/library" element={<LibraryPage/>}/>
      <Route path="/parameters" element={<Parameters/>}/>
      <Route path="/beat" element={<BeatEditor/>}/>
      <Route path="/profile" element={<Profile/>}/>
    </Route>
    <Route path="*" element={<Navigate to="/login" replace/>}/>
  </Routes>;
}
function Login() {
  const [status,setStatus]=useState<'idle'|'loading'|'error'>('idle');
  const [error,setError]=useState('');
  const signIn=async()=>{setStatus('loading');setError('');try{await authService.signInWithGoogle();}catch(reason){setError(serviceErrorMessage(reason));setStatus('error');}};
  return <main className="login"><div className="login-brand"><Logo/><h1>Build beats<br/>from everyday<br/><em>sounds.</em></h1></div>
    <div className="login-form"><div className="login-card"><h2>Sign in</h2>
      <button className="button google" onClick={signIn} disabled={status==='loading'}><span className="google-g">G</span>{status==='loading'?'Connecting…':'Continue with Google'}<ArrowRight size={18}/></button>
      {error&&<p className="service-message error" role="alert">{error}</p>}
    </div></div>
  </main>;
}
function Workflow() {
  const {pathname}=useLocation();
  if(pathname==='/profile')return null;
  const steps=[{path:'/library',name:'Sounds'},{path:'/parameters',name:'Parameters'},{path:'/beat',name:'Listen & export'}];
  return <nav className="workflow" aria-label="Create a beat steps">{steps.map((step,index)=><div className="workflow-step" key={step.path}>
    <Link to={step.path} aria-current={pathname===step.path?'step':undefined} className={pathname===step.path?'current':''}><span>{index+1}</span>{step.name}</Link>
    {index<2&&<ArrowRight size={28}/>}
  </div>)}</nav>;
}
function Shell() {
  const {pathname}=useLocation();
  return <div className="app-shell"><header className="app-header"><div className="app-header-inner"><Logo/>
    <nav className="app-nav" aria-label="Main navigation"><Link to="/library" className={pathname!=='/profile'?'active':''}><AudioLines size={19}/>Create a beat</Link><NavLink to="/profile"><span className="avatar">AM</span>Profile</NavLink></nav>
  </div></header><div className="workspace"><Workflow/><Outlet/></div></div>;
}
function ActionDialog({title,onClose,children}:{title:string;onClose:()=>void;children?:ReactNode}) {
  return <Modal title={title} onClose={onClose}>{children}<div className="modal-actions"><button className="button secondary" onClick={onClose}>Cancel</button></div></Modal>;
}

type RecordingPhase='idle'|'requesting'|'countdown'|'recording'|'review'|'saving'|'error';
function RecordDialog({onClose}:{onClose:()=>void}) {
  const [phase,setPhase]=useState<RecordingPhase>('idle');
  const [countdown,setCountdown]=useState(3);
  const [recordingUrl,setRecordingUrl]=useState('');
  const [recordingBlob,setRecordingBlob]=useState<Blob|null>(null);
  const [error,setError]=useState('');
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
    setRecordingUrl('');setRecordingBlob(null);setError('');setCountdown(3);setPhase('idle');
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
        setRecordingBlob(blob);setRecordingUrl(url);setPhase('review');
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
    setPhase('saving');setError('');
    try{await soundService.uploadRecording({name:'New recording',blob:recordingBlob});onClose();}
    catch(reason){setError(serviceErrorMessage(reason));setPhase('review');}
  };
  const close=()=>{clearResources();onClose();};

  return <Modal title="Record sound" onClose={close}>
    <div className="capture-zone" aria-live="polite">
      {phase==='idle'&&<><button className="record-circle" onClick={startCapture} aria-label="Start three second countdown"><Mic size={30}/></button><strong>Ready to record?</strong><span>You’ll get a 3-second countdown. Maximum duration: 1.5 seconds.</span></>}
      {phase==='requesting'&&<><Mic size={34}/><strong>Waiting for microphone…</strong><span>Approve access in your browser to begin the countdown.</span></>}
      {phase==='countdown'&&<><strong className="countdown-number">{countdown}</strong><span>Get your sound ready</span></>}
      {phase==='recording'&&<><span className="recording-pulse"/><strong>Recording…</strong><span>Capturing 1.5 seconds</span></>}
      {phase==='review'&&recordingUrl&&<><strong>Recording ready</strong><audio className="recording-preview" controls src={recordingUrl}/><span>Review your sound before saving it.</span></>}
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
  const [tab,setTab]=useState<'mine'|'public'>('mine');
  const [query,setQuery]=useState('');
  const [selectedIds,setSelectedIds]=useState(()=>sounds.slice(0,2).map(sound=>sound.id));
  const selectedSounds=sounds.filter(sound=>selectedIds.includes(sound.id));
  const toggleSelection=(id:string)=>setSelectedIds(current=>current.includes(id)?current.filter(value=>value!==id):[...current,id]);
  const [dialog,setDialog]=useState<{type:string;sound?:SoundView}|null>(null);
  const [serviceError,setServiceError]=useState('');
  const [busy,setBusy]=useState('');
  const shown=sounds.filter(sound=>(tab==='mine'?sound.owned:sound.visibility==='public')&&sound.name.toLowerCase().includes(query.toLowerCase()));
  const run=async(label:string,operation:()=>Promise<unknown>)=>{setBusy(label);setServiceError('');try{await operation();}catch(reason){setServiceError(serviceErrorMessage(reason));}finally{setBusy('');}};
  useEffect(()=>{let current=true;soundService.list({scope:tab,query}).catch(reason=>{if(current)setServiceError(serviceErrorMessage(reason));});return()=>{current=false;};},[tab,query]);
  return <main className="page library-page">
    <PageHeader title="Select your sounds" description="Record sounds up to 1.5 seconds and select samples for your beat."/>
    <div className="library-layout"><section className="sound-library">
      <div className="library-controls"><div className="library-tab-actions">
        <div className="library-tabs" role="tablist" aria-label="Sound library" onKeyDown={e=>{if(e.key==='ArrowLeft'||e.key==='ArrowRight'){e.preventDefault();setTab(tab==='mine'?'public':'mine');e.currentTarget.querySelectorAll<HTMLButtonElement>('button')[tab==='mine'?1:0]?.focus();}}}>
          <button role="tab" aria-selected={tab==='mine'} className={tab==='mine'?'active':''} onClick={()=>setTab('mine')}><LockKeyhole size={16}/>My sounds<span>{sounds.filter(s=>s.owned).length}</span></button>
          <button role="tab" aria-selected={tab==='public'} className={tab==='public'?'active':''} onClick={()=>setTab('public')}><Globe2 size={16}/>Community<span>{sounds.filter(s=>s.visibility==='public').length}</span></button>
        </div>
        <button className="button primary record-action" onClick={()=>setDialog({type:'Record sound'})}><Mic size={21}/>Record a sound</button>
      </div><div className="library-tools"><label className="search"><Search size={17}/><input aria-label="Search sounds" placeholder="Find a sound…" value={query} onChange={event=>setQuery(event.target.value)}/></label></div></div>
      <div className="sound-grid">{shown.map(sound=><article key={sound.id} className={`sound-card ${sound.owned?'owned-sound':''} visibility-${sound.visibility} ${selectedSounds.some(s=>s.id===sound.id)?'selected':''}`}>
        <div className="sound-card-top">{sound.owned?<button className="delete-sound-button" aria-label={`Delete ${sound.name}`} onClick={()=>setDialog({type:'Delete sound',sound})}><Trash2 size={15}/>Delete</button>:<button className="icon-button" aria-label={`Report ${sound.name}`} onClick={()=>setDialog({type:'Report sound',sound})}><Flag size={15}/></button>}</div>
        <div className="sound-name"><h3>{sound.name}</h3><span className="visibility-badge">{sound.visibility==='public'?<Globe2 size={12}/>:<LockKeyhole size={12}/>} {sound.visibility==='public'?'Public':'Private'}</span></div>
        <div className="sound-preview"><button className="preview-button" aria-label={`Preview ${sound.name}`} disabled={busy===`preview-${sound.id}`} onClick={()=>run(`preview-${sound.id}`,async()=>{const url=await soundService.getPlaybackUrl(sound.id);await new Audio(url).play();})}><Play size={17} fill="currentColor"/></button><Wave values={sound.waveform}/></div>
        <div className="sound-card-bottom">{sound.owned?<button className="add-button publish-button" disabled={busy===`visibility-${sound.id}`} onClick={()=>run(`visibility-${sound.id}`,()=>soundService.setVisibility(sound.id,sound.visibility==='private'?'public':'private'))}>{sound.visibility==='private'?<Globe2 size={14}/>:<LockKeyhole size={14}/>}Make {sound.visibility==='private'?'public':'private'}</button>:<span>by {sound.creator}</span>}
          <button className={`add-button ${selectedIds.includes(sound.id)?'added':''}`} aria-pressed={selectedIds.includes(sound.id)} onClick={()=>toggleSelection(sound.id)}>{selectedSounds.some(s=>s.id===sound.id)?<><Check size={14}/>Added</>:<><Plus size={14}/>Add to beat</>}</button>
        </div>
      </article>)}</div>
      {serviceError&&<p className="service-message error" role="alert">{serviceError}</p>}
    </section><aside className="beat-tray"><div className="mobile-tray-title"><div className="tray-heading"><h3>Selected sounds</h3><span className="count">{selectedSounds.length}</span></div></div>
      <div className="tray-sounds">{selectedSounds.map((sound,index)=><div className="tray-sound" key={sound.id}><span className="track-number">{String(index+1).padStart(2,'0')}</span><div><strong>{sound.name}</strong></div><button className="icon-button" aria-label={`Remove ${sound.name}`} onClick={()=>toggleSelection(sound.id)}><X size={14}/></button></div>)}</div>
      <Link to="/parameters" className="button primary full continue-action">Continue to parameters<ArrowRight size={21}/></Link>
    </aside></div>
    {dialog?.type==='Record sound'&&<RecordDialog onClose={()=>setDialog(null)}/>}
    {dialog&&dialog.type!=='Record sound'&&<ActionDialog title={dialog.type} onClose={()=>setDialog(null)}>
      {dialog.type==='Delete sound'&&<><p className="muted">Delete “{dialog.sound?.name}”?</p><button className="button secondary" disabled={busy==='delete'} onClick={()=>dialog.sound&&run('delete',()=>soundService.delete(dialog.sound!.id))}>Delete sound</button></>}
      {dialog.type==='Report sound'&&<><label className="form-label">Reason<select id="report-reason" defaultValue=""><option value="">Choose a reason</option><option>Inappropriate content</option></select></label><button className="button primary" disabled={busy==='report'} onClick={()=>dialog.sound&&run('report',()=>soundService.report(dialog.sound!.id,(document.getElementById('report-reason') as HTMLSelectElement).value))}>Submit report</button></>}
      {serviceError&&<p className="service-message error" role="alert">{serviceError}</p>}
    </ActionDialog>}
  </main>;
}
function SelectField({label,value,options,onChange}:{label:string;value:string;options:readonly string[];onChange?:(value:string)=>void}) {
  return <label className="form-label">{label}<select value={value} onChange={event=>onChange?.(event.target.value)}>{options.map(option=><option key={option} value={option}>{option[0].toUpperCase()+option.slice(1)}</option>)}</select></label>;
}
function Parameters() {
  const [tempo,setTempo]=useState(120);
  const [genre,setGenre]=useState('electronic');
  const [ensemble,setEnsemble]=useState('band');
  const [meter,setMeter]=useState('4/4');
  const [key,setKey]=useState('0');
  const [mode,setMode]=useState('none');
  const [generating,setGenerating]=useState(false);
  const [error,setError]=useState('');
  const navigate=useNavigate();
  const generate=async()=>{
    setGenerating(true);setError('');
    try{
      const beat=await beatService.generate({soundIds:selectedSounds.map(sound=>sound.id),parameters:{tempo,genre,ensemble,meter,key,mode,instruments:Object.fromEntries(selectedSounds.map(sound=>[sound.id,'drums']))}});
      navigate(`/beat?id=${encodeURIComponent(beat.id)}`);
    }catch(reason){setError(serviceErrorMessage(reason));}finally{setGenerating(false);}
  };
  return <main className="page"><PageHeader title="Set beat parameters" description="Choose a tempo and style for your two-bar beat."/>
    <div className="parameters-layout"><section className="panel parameter-panel">
      <div className="tempo-heading"><label htmlFor="tempo">Tempo</label><div><output htmlFor="tempo" className="tempo-value">{tempo}</output><span>BPM</span></div></div>
      <input id="tempo" aria-label="Tempo" type="range" min={MIN_TEMPO} max={MAX_TEMPO} value={tempo} onChange={event=>setTempo(Number(event.target.value))}/>
      <div className="range-labels"><span>{MIN_TEMPO} BPM</span><span>{MAX_TEMPO} BPM</span></div>
      <SelectField label="Style / genre" value={genre} options={genres} onChange={setGenre}/>
      <details className="advanced"><summary><Settings2 size={18}/><span className="section-heading">Advanced settings<InfoTip label="advanced settings" text="Key, meter, and instrument assignments."/></span><ChevronDown size={17}/></summary>
        <div className="advanced-grid"><SelectField label="Ensemble" value={ensemble} options={ensembles} onChange={setEnsemble}/><SelectField label="Time signature" value={meter} options={['4/4','3/4','6/8']} onChange={setMeter}/><SelectField label="Key signature" value={key} options={['-7','-6','-5','-4','-3','-2','-1','0','1','2','3','4','5','6','7']} onChange={setKey}/><SelectField label="Mode" value={mode} options={modes} onChange={setMode}/></div>
        <div className="instrument-list"><div className="section-heading"><h3>Instrument assignments</h3><InfoTip label="instrument assignments" text="Assign an instrument track to each sound."/></div>
          {selectedSounds.map(sound=><label className="form-label" key={sound.id}>{sound.name}<select defaultValue="drums"><option value="drums">Percussion / drum track</option>{gmNames.map((name,index)=><option key={index} value={index}>{index} · {name}</option>)}</select></label>)}
        </div>
      </details>
    </section><aside className="panel session-summary"><h2>Your settings</h2>{[['Sounds','2'],['Length','2 bars'],['Tempo',`${tempo} BPM`],['Style',genre]].map(([label,value])=><div className="summary-row" key={label}><span>{label}</span><strong>{value}</strong></div>)}
      <button className="button primary full" onClick={generate} disabled={generating}>{generating?'Generating…':'Generate beat'}</button>{error&&<p className="service-message error" role="alert">{error}</p>}<Link className="back-link" to="/library"><ArrowLeft size={14}/>Back to sounds</Link>
    </aside></div>
  </main>;
}
function BeatEditor() {
  const {search}=useLocation();
  const beatId=new URLSearchParams(search).get('id')??outputPreview.id;
  const [output,setOutput]=useState<BeatOutput|null>(null);
  const [error,setError]=useState('');
  const [loading,setLoading]=useState(true);
  const [playing,setPlaying]=useState(false);
  const [time,setTime]=useState(0);
  const audioRef=useRef<HTMLAudioElement>(null);
  useEffect(()=>{let current=true;setLoading(true);beatService.getOutput(beatId).then(value=>{if(current){setOutput(value);setError('');}}).catch(reason=>{if(current)setError(serviceErrorMessage(reason));}).finally(()=>{if(current)setLoading(false);});return()=>{current=false;};},[beatId]);
  const duration=output?.durationSeconds??outputPreview.durationSeconds;
  const values=output?.waveform??outputPreview.waveform;
  const togglePlayback=async()=>{const audio=audioRef.current;if(!audio||!output?.audioUrl)return;if(audio.paused)await audio.play();else audio.pause();};
  const seek=(value:number)=>{const audio=audioRef.current;setTime(value);if(audio)audio.currentTime=value;};
  const download=async()=>{
    if(!output)return;
    setError('');
    try{const url=output.downloadUrl||await beatService.getExportUrl(output.id);window.location.assign(url);}catch(reason){setError(serviceErrorMessage(reason));}
  };
  const format=(seconds:number)=>`${Math.floor(seconds/60)}:${Math.floor(seconds%60).toString().padStart(2,'0')}`;
  const unavailable=!output?.audioUrl;
  return <main className="page output-page"><PageHeader title="Your beat" description="Listen to your generated audio and export it as an MP3."><Link className="button secondary" to="/parameters"><Settings2 size={16}/>Parameters</Link></PageHeader>
    <section className="audio-output-card" aria-busy={loading}>
      <div className="audio-output-heading"><div><span className="eyebrow">Generated output</span><h2>{output?.name??outputPreview.name}</h2></div><button className="button primary" onClick={download} disabled={!output||loading}><ArrowDownToLine size={17}/>Download MP3</button></div>
      <div className="output-waveform" aria-label="Audio waveform visualization">{values.map((value,index)=><span key={index} style={{height:`${18+value*78}%`}} className={index/values.length<time/duration?'played':''}/>)}</div>
      <div className="audio-controls">
        <button className="transport-play" onClick={togglePlayback} disabled={unavailable} aria-label={playing?'Pause beat':'Play beat'}>{playing?<Pause size={22} fill="currentColor"/>:<Play size={22} fill="currentColor"/>}</button>
        <span className="audio-time">{format(time)}</span>
        <input aria-label="Beat playback position" type="range" min={0} max={duration} step={0.01} value={Math.min(time,duration)} disabled={unavailable} onChange={event=>seek(Number(event.target.value))}/>
        <span className="audio-time">{format(duration)}</span>
      </div>
      {output?.audioUrl&&<audio ref={audioRef} src={output.audioUrl} onPlay={()=>setPlaying(true)} onPause={()=>setPlaying(false)} onTimeUpdate={event=>setTime(event.currentTarget.currentTime)} onEnded={()=>setPlaying(false)}/>}
      {error&&<p className="service-message error" role="alert">{error}</p>}
      {!loading&&unavailable&&<p className="output-empty">The player and export controls will activate when the beat output API returns an audio file.</p>}
    </section>
    <Link className="back-link" to="/library"><ArrowLeft size={15}/>Back to sounds</Link>
  </main>;
}
function Profile() {
  const [username,setUsername]=useState('Alex Morgan');
  const [email,setEmail]=useState('alex.morgan@example.com');
  const [busy,setBusy]=useState('');
  const [error,setError]=useState('');
  const photoInput=useRef<HTMLInputElement>(null);
  const run=async(label:string,operation:()=>Promise<unknown>)=>{setBusy(label);setError('');try{await operation();}catch(reason){setError(serviceErrorMessage(reason));}finally{setBusy('');}};
  useEffect(()=>{let current=true;profileService.get().then(profile=>{if(current){setUsername(profile.username);setEmail(profile.email);}}).catch(reason=>{if(current)setError(serviceErrorMessage(reason));});return()=>{current=false;};},[]);
  return <main className="page"><PageHeader title="Profile" description="Manage your profile and account settings."/><section className="panel profile-panel">
    <div className="profile-avatar"><span className="avatar">AM</span><div><div className="section-heading profile-photo-heading"><strong>Your photo</strong><InfoTip label="profile photo" text="Choose a photo for your profile."/></div><input ref={photoInput} className="visually-hidden" type="file" accept="image/*" onChange={event=>{const file=event.target.files?.[0];if(file)run('photo',()=>profileService.uploadPhoto(file));}}/><button className="button secondary" disabled={busy==='photo'} onClick={()=>photoInput.current?.click()}><Upload size={15}/>{busy==='photo'?'Uploading…':'Change photo'}</button></div></div>
    <div className="form-stack"><label>Username<input value={username} onChange={event=>setUsername(event.target.value)}/></label><label>Email address<input value={email} onChange={event=>setEmail(event.target.value)}/></label>
      <div className="account-help"><LockKeyhole size={20}/><div><strong>Password & account security</strong><p>Manage your password through Google.</p></div></div>
      <button className="button primary" disabled={busy==='save'} onClick={()=>run('save',()=>profileService.update({username,email}))}>{busy==='save'?'Saving…':'Save changes'}</button>
      {error&&<p className="service-message error" role="alert">{error}</p>}
    </div><div className="profile-signout"><button className="button secondary" disabled={busy==='signout'} onClick={()=>run('signout',()=>authService.signOut())}><LogOut size={16}/>{busy==='signout'?'Signing out…':'Sign out'}</button></div>
  </section></main>;
}
