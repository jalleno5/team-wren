export interface ClippedAudio {
  blob:Blob;
  durationSeconds:number;
}

export async function clipAudioBlob(source:Blob,startSeconds:number,endSeconds:number):Promise<ClippedAudio>{
  let context:AudioContext|undefined;
  try{
    context=new AudioContext();
    const decoded=await context.decodeAudioData(await source.arrayBuffer());
    const startFrame=Math.max(0,Math.min(decoded.length-1,Math.floor(startSeconds*decoded.sampleRate)));
    const endFrame=Math.max(startFrame+1,Math.min(decoded.length,Math.ceil(endSeconds*decoded.sampleRate)));
    const frameCount=endFrame-startFrame;
    const channels=Array.from({length:decoded.numberOfChannels},(_,channel)=>decoded.getChannelData(channel).slice(startFrame,endFrame));
    return {blob:new Blob([encodeWave(channels,decoded.sampleRate,frameCount)],{type:'audio/wav'}),durationSeconds:frameCount/decoded.sampleRate};
  }catch{
    throw new Error('The selected audio could not be clipped. Try recording the sound again.');
  }finally{
    await context?.close().catch(()=>undefined);
  }
}

function encodeWave(channels:Float32Array[],sampleRate:number,frameCount:number):ArrayBuffer{
  const channelCount=channels.length;
  const bytesPerSample=2;
  const dataLength=frameCount*channelCount*bytesPerSample;
  const buffer=new ArrayBuffer(44+dataLength);
  const view=new DataView(buffer);
  const write=(offset:number,value:string)=>{for(let index=0;index<value.length;index++)view.setUint8(offset+index,value.charCodeAt(index));};
  write(0,'RIFF');view.setUint32(4,36+dataLength,true);write(8,'WAVE');write(12,'fmt ');
  view.setUint32(16,16,true);view.setUint16(20,1,true);view.setUint16(22,channelCount,true);view.setUint32(24,sampleRate,true);
  view.setUint32(28,sampleRate*channelCount*bytesPerSample,true);view.setUint16(32,channelCount*bytesPerSample,true);view.setUint16(34,16,true);
  write(36,'data');view.setUint32(40,dataLength,true);
  let offset=44;
  for(let frame=0;frame<frameCount;frame++)for(let channel=0;channel<channelCount;channel++){
    const sample=Math.max(-1,Math.min(1,channels[channel][frame]??0));
    view.setInt16(offset,sample<0?sample*0x8000:sample*0x7fff,true);offset+=bytesPerSample;
  }
  return buffer;
}
