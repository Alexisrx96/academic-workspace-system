// @ts-nocheck
export const state={route:{name:'today'},workspace:null,course:null,source:null,session:null,metrics:null};
export function navigate(route){state.route=route; window.location.hash=route.name==='today'?'#/hoy':`#/${route.name}/${encodeURIComponent(route.value||'')}`; window.dispatchEvent(new CustomEvent('routechange'));}
export function parseRoute(){const [_,rawName,value]=window.location.hash.split('/'); const name=rawName==='hoy'?'today':rawName; return name?{name,value:decodeURIComponent(value||'')}:{name:'today'};}