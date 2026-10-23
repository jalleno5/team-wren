import type { SoundView, LaneView } from './model';

const waveform = [0.12,0.2,0.44,0.32,0.72,0.88,0.6,0.48,0.94,0.65,0.4,0.3,0.52,0.7,0.36,0.28,0.46,0.62,0.3,0.16,0.25,0.14,0.08,0.12];
// Static illustration values only: these are not derived from playable audio.
export const sounds:SoundView[] = [
  {id:'ceramic',name:'Ceramic tap',creator:'Alex Morgan',owned:true,visibility:'private',waveform},
  {id:'keys',name:'Keys on the counter',creator:'Alex Morgan',owned:true,visibility:'private',waveform:[...waveform].reverse()},
  {id:'tin',name:'Coffee tin kick',creator:'Alex Morgan',owned:true,visibility:'public',waveform},
  {id:'rain',name:'Rain on the window',creator:'Alex Morgan',owned:true,visibility:'private',waveform},
  {id:'bottle',name:'Bottle cap snap',creator:'Maya Chen',owned:false,visibility:'public',waveform},
  {id:'paper',name:'Paper bag shuffle',creator:'Noah Kim',owned:false,visibility:'public',waveform},
];
export const selectedSounds = sounds.slice(0,2);
export const lanes:LaneView[] = [
  {soundId:'ceramic',activeSteps:[0,4,8,12,16,20,24,28]},
  {soundId:'keys',activeSteps:[4,12,20,28]},
];
