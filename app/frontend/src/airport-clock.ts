export function localClock(value:string,zone:string){
  if(!value)return '—';
  const date=new Date(/(Z|[+-]\d\d:\d\d)$/i.test(value)?value:value+'Z');
  return new Intl.DateTimeFormat('en-US',{timeZone:zone,hour:'numeric',minute:'2-digit',timeZoneName:'short'}).format(date);
}
export function countdown(seconds:number){
  const t=Math.max(0,Math.ceil(seconds));
  return String(Math.floor(t/60)).padStart(2,'0')+':'+String(t%60).padStart(2,'0');
}
