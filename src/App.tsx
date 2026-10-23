import { useEffect, useId, useRef, useState, type ReactNode } from 'react';
import { Link, NavLink, Navigate, Outlet, Route, Routes, useLocation } from 'react-router-dom';
import { ArrowDownToLine, ArrowLeft, ArrowRight, AudioLines, Check, ChevronDown, Flag, Globe2, Info, LockKeyhole, LogOut, Mic, Play, Plus, Search, Settings2, Square, Trash2, Upload, Volume2, X } from 'lucide-react';
import { MIN_TEMPO, MAX_TEMPO, ensembles, genres, gmNames, modes, type SoundView } from './model';
import { sounds, selectedSounds, lanes } from './fixtures';
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
  return <main className="login"><div className="login-brand"><Logo/><h1>Build beats<br/>from everyday<br/><em>sounds.</em></h1></div>
    <div className="login-form"><div className="login-card"><h2>Sign in</h2>
      <Link className="button google" to="/library"><span className="google-g">G</span>Continue with Google<ArrowRight size={18}/></Link>
      
    </div></div>
  </main>;
}
function Workflow() {
  const {pathname}=useLocation();
  if(pathname==='/profile')return null;
  const steps=[{path:'/library',name:'Sounds'},{path:'/parameters',name:'Parameters'},{path:'/beat',name:'Edit & export'}];
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
function LibraryPage() {
  const [tab,setTab]=useState<'mine'|'public'>('mine');
  const [selectedIds,setSelectedIds]=useState(()=>sounds.slice(0,2).map(sound=>sound.id));
  const selectedSounds=sounds.filter(sound=>selectedIds.includes(sound.id));
  const toggleSelection=(id:string)=>setSelectedIds(current=>current.includes(id)?current.filter(value=>value!==id):[...current,id]);
  const [dialog,setDialog]=useState<{type:string;sound?:SoundView}|null>(null);
  const shown=sounds.filter(sound=>tab==='mine'?sound.owned:sound.visibility==='public');
  return <main className="page library-page">
    <PageHeader title="Select your sounds" description="Record sounds up to 1.5 seconds and select samples for your beat."/>
    <div className="library-layout"><section className="sound-library">
      <div className="library-controls"><div className="library-tab-actions">
        <div className="library-tabs" role="tablist" aria-label="Sound library" onKeyDown={e=>{if(e.key==='ArrowLeft'||e.key==='ArrowRight'){e.preventDefault();setTab(tab==='mine'?'public':'mine');e.currentTarget.querySelectorAll<HTMLButtonElement>('button')[tab==='mine'?1:0]?.focus();}}}>
          <button role="tab" aria-selected={tab==='mine'} className={tab==='mine'?'active':''} onClick={()=>setTab('mine')}><LockKeyhole size={16}/>My sounds<span>{sounds.filter(s=>s.owned).length}</span></button>
          <button role="tab" aria-selected={tab==='public'} className={tab==='public'?'active':''} onClick={()=>setTab('public')}><Globe2 size={16}/>Community<span>{sounds.filter(s=>s.visibility==='public').length}</span></button>
        </div>
        <button className="button primary record-action" onClick={()=>setDialog({type:'Record sound'})}><Mic size={21}/>Record a sound</button>
      </div><div className="library-tools"><label className="search"><Search size={17}/><input aria-label="Search sounds" placeholder="Find a sound…"/></label></div></div>
      <div className="sound-grid">{shown.map(sound=><article key={sound.id} className={`sound-card ${sound.owned?'owned-sound':''} visibility-${sound.visibility} ${selectedSounds.some(s=>s.id===sound.id)?'selected':''}`}>
        <div className="sound-card-top">{sound.owned?<button className="delete-sound-button" aria-label={`Delete ${sound.name}`} onClick={()=>setDialog({type:'Delete sound',sound})}><Trash2 size={15}/>Delete</button>:<button className="icon-button" aria-label={`Report ${sound.name}`} onClick={()=>setDialog({type:'Report sound',sound})}><Flag size={15}/></button>}</div>
        <div className="sound-name"><h3>{sound.name}</h3><span className="visibility-badge">{sound.visibility==='public'?<Globe2 size={12}/>:<LockKeyhole size={12}/>} {sound.visibility==='public'?'Public':'Private'}</span></div>
        <div className="sound-preview"><button className="preview-button" aria-label={`Preview ${sound.name}`}><Play size={17} fill="currentColor"/></button><Wave values={sound.waveform}/></div>
        <div className="sound-card-bottom">{sound.owned?<button className="add-button publish-button">{sound.visibility==='private'?<Globe2 size={14}/>:<LockKeyhole size={14}/>}Make {sound.visibility==='private'?'public':'private'}</button>:<span>by {sound.creator}</span>}
          <button className={`add-button ${selectedIds.includes(sound.id)?'added':''}`} aria-pressed={selectedIds.includes(sound.id)} onClick={()=>toggleSelection(sound.id)}>{selectedSounds.some(s=>s.id===sound.id)?<><Check size={14}/>Added</>:<><Plus size={14}/>Add to beat</>}</button>
        </div>
      </article>)}</div>
    </section><aside className="beat-tray"><div className="mobile-tray-title"><div className="tray-heading"><h3>Selected sounds</h3><span className="count">{selectedSounds.length}</span></div></div>
      <div className="tray-sounds">{selectedSounds.map((sound,index)=><div className="tray-sound" key={sound.id}><span className="track-number">{String(index+1).padStart(2,'0')}</span><div><strong>{sound.name}</strong></div><button className="icon-button" aria-label={`Remove ${sound.name}`} onClick={()=>toggleSelection(sound.id)}><X size={14}/></button></div>)}</div>
      <Link to="/parameters" className="button primary full continue-action">Continue to parameters<ArrowRight size={21}/></Link>
    </aside></div>
    {dialog&&<ActionDialog title={dialog.type} onClose={()=>setDialog(null)}>
      {dialog.type==='Record sound'&&<div className="capture-zone"><button className="record-circle" aria-label="Start recording"><Mic size={30}/></button><span>Maximum duration: 1.5 seconds</span></div>}
      {dialog.type==='Delete sound'&&<><p className="muted">Delete “{dialog.sound?.name}”?</p><button className="button secondary" onClick={()=>setDialog(null)}>Delete sound</button></>}
      {dialog.type==='Report sound'&&<label className="form-label">Reason<select defaultValue=""><option value="">Choose a reason</option><option>Inappropriate content</option></select></label>}
    </ActionDialog>}
  </main>;
}
function SelectField({label,value,options}:{label:string;value:string;options:readonly string[]}) {
  return <label className="form-label">{label}<select defaultValue={value}>{options.map(option=><option key={option} value={option}>{option[0].toUpperCase()+option.slice(1)}</option>)}</select></label>;
}
function Parameters() {
  const [tempo,setTempo]=useState(120);
  return <main className="page"><PageHeader title="Set beat parameters" description="Choose a tempo and style for your two-bar beat."/>
    <div className="parameters-layout"><section className="panel parameter-panel">
      <div className="tempo-heading"><label htmlFor="tempo">Tempo</label><div><output htmlFor="tempo" className="tempo-value">{tempo}</output><span>BPM</span></div></div>
      <input id="tempo" aria-label="Tempo" type="range" min={MIN_TEMPO} max={MAX_TEMPO} value={tempo} onChange={event=>setTempo(Number(event.target.value))}/>
      <div className="range-labels"><span>{MIN_TEMPO} BPM</span><span>{MAX_TEMPO} BPM</span></div>
      <SelectField label="Style / genre" value="electronic" options={genres}/>
      <details className="advanced"><summary><Settings2 size={18}/><span className="section-heading">Advanced settings<InfoTip label="advanced settings" text="Key, meter, and instrument assignments."/></span><ChevronDown size={17}/></summary>
        <div className="advanced-grid"><SelectField label="Ensemble" value="band" options={ensembles}/><SelectField label="Time signature" value="4/4" options={['4/4','3/4','6/8']}/><SelectField label="Key signature" value="0" options={['-7','-6','-5','-4','-3','-2','-1','0','1','2','3','4','5','6','7']}/><SelectField label="Mode" value="none" options={modes}/></div>
        <div className="instrument-list"><div className="section-heading"><h3>Instrument assignments</h3><InfoTip label="instrument assignments" text="Assign an instrument track to each sound."/></div>
          {selectedSounds.map(sound=><label className="form-label" key={sound.id}>{sound.name}<select defaultValue="drums"><option value="drums">Percussion / drum track</option>{gmNames.map((name,index)=><option key={index} value={index}>{index} · {name}</option>)}</select></label>)}
        </div>
      </details>
    </section><aside className="panel session-summary"><h2>Your settings</h2>{[['Sounds','2'],['Length','2 bars'],['Steps','32'],['Tempo',`${tempo} BPM`],['Style','electronic']].map(([label,value])=><div className="summary-row" key={label}><span>{label}</span><strong>{value}</strong></div>)}
      <Link className="button primary full" to="/beat">Generate & edit</Link><Link className="back-link" to="/library"><ArrowLeft size={14}/>Back to sounds</Link>
    </aside></div>
  </main>;
}
function ResponsiveSequencer() {
  const container=useRef<HTMLDivElement>(null);
  const [width,setWidth]=useState(0);
  useEffect(()=>{
    const element=container.current;
    if(!element)return;
    const observer=new ResizeObserver(entries=>setWidth(entries[0].contentRect.width));
    observer.observe(element);
    return()=>observer.disconnect();
  },[]);
  const gridWidth=Math.max(0,width-(width>=640?195:0));
  const groupSize=[32,16,8,4,2,1].find(size=>gridWidth>=size*32+(size-1)*5)??1;
  const groups=Array.from({length:Math.ceil(32/groupSize)},(_,i)=>i*groupSize);
  return <div className="sequencer-area"><div className="sequencer responsive-sequencer" ref={container}>{groups.map(start=>{
    const end=Math.min(start+groupSize,32);
    return <section className="sequence-group" key={start} aria-label={`Steps ${start+1} to ${end}`}>
      {lanes.map((lane,index)=><div className="seq-row" key={lane.soundId}>
        <div className="lane-label"><div><span className="track-number">{String(index+1).padStart(2,'0')}</span><strong>{sounds.find(s=>s.id===lane.soundId)?.name}</strong><button className="icon-button" aria-label={`Mute lane ${index+1}`}><Volume2 size={15}/></button></div><input aria-label={`Lane ${index+1} volume`} type="range" min={0} max={1} step={0.01} defaultValue={0.8}/></div>
        <div className="steps" style={{gridTemplateColumns:`repeat(${end-start},minmax(0,1fr))`}}>{Array.from({length:end-start},(_,offset)=>{const step=start+offset;const active=lane.activeSteps.includes(step);return <button key={step} aria-label={`Lane ${index+1}, step ${step+1}`} aria-pressed={active} className={`step ${active?'on':''} ${step%4===0?'beat-start':''}`}><span style={{height:'80%'}}/></button>;})}</div>
      </div>)}
    </section>;
  })}</div></div>;
}
function BeatEditor() {
  const [exportOpen,setExportOpen]=useState(false);
  return <main className="page"><PageHeader title="Edit & export" description="Adjust your pattern and export your beat."><Link className="button secondary" to="/parameters"><Settings2 size={16}/>Parameters</Link><button className="button primary" onClick={()=>setExportOpen(true)}><ArrowDownToLine size={17}/>MP3 export</button></PageHeader>
    <section className="studio panel"><div className="beat-transport-panel"><div className="studio-heading"><div><input className="beat-name" aria-label="Beat name" defaultValue="Untitled Beat"/></div></div><div className="transport"><button className="transport-play" aria-label="Play"><Play size={23} fill="currentColor"/></button><button className="icon-button" aria-label="Stop"><Square size={17}/></button></div></div><ResponsiveSequencer/></section>
    <Link className="back-link" to="/library"><ArrowLeft size={15}/>Back to sounds</Link>
    {exportOpen&&<ActionDialog title="MP3 export" onClose={()=>setExportOpen(false)}><button className="button primary" onClick={()=>setExportOpen(false)}>Export MP3</button></ActionDialog>}
  </main>;
}
function Profile() {
  return <main className="page"><PageHeader title="Profile" description="Manage your profile and account settings."/><section className="panel profile-panel">
    <div className="profile-avatar"><span className="avatar">AM</span><div><div className="section-heading profile-photo-heading"><strong>Your photo</strong><InfoTip label="profile photo" text="Choose a photo for your profile."/></div><button className="button secondary"><Upload size={15}/>Change photo</button></div></div>
    <div className="form-stack"><label>Username<input defaultValue="Alex Morgan"/></label><label>Email address<input defaultValue="alex.morgan@example.com"/></label>
      <div className="account-help"><LockKeyhole size={20}/><div><strong>Password & account security</strong><p>Manage your password through Google.</p></div></div>
      <button className="button primary">Save changes</button>
    </div><div className="profile-signout"><Link className="button secondary" to="/login"><LogOut size={16}/>Sign out</Link></div>
  </section></main>;
}
