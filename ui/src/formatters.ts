// @ts-nocheck
export const phaseLabels={preflight:'Preparación',diagnostic:'Diagnóstico',retrieval:'Recuperación',source_review:'Fuente',practice:'Práctica',validation:'Validación',evidence:'Evidencia',review_scheduling:'Repaso'};
export const modeLabels={guided:'Guiada',explicit_validation:'Validación explícita',manual_verification:'Comprobación manual',adversarial_source:'Revisión adversarial'};
export const statusLabels={active:'En curso',blocked:'Bloqueada',completed:'Completada',paused:'Pausada',planned:'Planificada'};
export const escapeHtml=value=>String(value??'').replace(/[&<>"']/g,char=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[char]));
export const markdownTitle=value=>String(value||'').replace(/\*\*/g,'').replace(/\[([^\]]+)\]\([^)]*\)/g,'$1');