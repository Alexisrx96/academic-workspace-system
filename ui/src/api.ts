// @ts-nocheck
export async function api(path, options = {}) { const response = await fetch(path, { headers: { 'Content-Type': 'application/json' }, ...options }); const data = await response.json(); if (!response.ok) throw new Error(data.error || JSON.stringify(data)); return data; }
export const getWorkspace = () => api('/api/workspace');
export const getMetrics = () => api('/api/metrics');
export const getSession = session_id => api(`/api/session?session_id=${encodeURIComponent(session_id)}`);
export const getCourse = code => api(`/api/course?code=${encodeURIComponent(code)}`);
export const getSource = path => api(`/api/source?path=${encodeURIComponent(path)}`);
export const startSession = data => api('/api/session/start', {method:'POST', body:JSON.stringify(data)});
export const recordAttempt = data => api('/api/session/attempt', {method:'POST', body:JSON.stringify(data)});
export const transitionSession = (session_id,status) => api('/api/session/transition', {method:'POST', body:JSON.stringify({session_id,status})});
export const completeSession = session_id => api('/api/session/complete', {method:'POST', body:JSON.stringify({session_id})});
export const saveSource=(path,content)=>api('/api/source/save',{method:'POST',body:JSON.stringify({path,content})});