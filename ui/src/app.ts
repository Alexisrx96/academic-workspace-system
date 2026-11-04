// @ts-nocheck
import { getWorkspace, getMetrics, getSession } from './api.js';
import { state, parseRoute, navigate } from './state.js';
import { todayView, courseView, sourceView, metricsView, sessionView, perform } from './views.js';

function bind(): void {
  document.querySelectorAll('[data-route]').forEach((element) => {
    element.onclick = () => {
      let route = element.dataset.route;
      if (route === 'back') route = state.previousRoute || { name: 'today' };
      else route = { name: route };
      navigate(route);
    };
  });
  document.querySelectorAll('[data-action]').forEach((element) => {
    element.onclick = () => perform(element.dataset.action, element).catch((error) => alert(error.message));
  });
}

function typesetMath(root: HTMLElement, tries = 0): void {
  if (window.MathJax?.typesetPromise) {
    window.MathJax.typesetPromise([root]).catch(() => {});
    return;
  }
  if (tries < 8) setTimeout(() => typesetMath(root, tries + 1), 250);
}

async function render(): Promise<void> {
  state.route = parseRoute();
  const root = document.querySelector<HTMLElement>('#app');
  try {
    if (state.route.name === 'today') {
      state.workspace = await getWorkspace();
      root.innerHTML = todayView();
    } else if (state.route.name === 'courses') {
      state.workspace = await getWorkspace();
      root.innerHTML = todayView();
      document.querySelector('#coursesSection')?.scrollIntoView();
    } else if (state.route.name === 'reviews') {
      state.workspace = await getWorkspace();
      root.innerHTML = todayView();
      document.querySelector('#coursesSection')?.nextElementSibling?.scrollIntoView();
    } else if (state.route.name === 'course') {
      root.innerHTML = await courseView(state.route.value);
    } else if (state.route.name === 'source') {
      root.innerHTML = await sourceView(state.route.value);
    } else if (state.route.name === 'metrics') {
      root.innerHTML = metricsView();
      const data = await getMetrics();
      document.querySelector('#metricsData').textContent = `Intentos: ${data.attempts} · Resultados: ${Object.keys(data.results).length} · Errores: ${Object.keys(data.errors).length}`;
    } else if (state.route.name === 'session') {
      state.session = await getSession(state.route.value);
      root.innerHTML = sessionView(state.session);
    } else {
      navigate({ name: 'today' });
      return;
    }
    bind();
    if (state.route.name === 'source') typesetMath(root);
  } catch (error) {
    root.innerHTML = '<section class="panel"><h1>No se pudo cargar esta vista</h1><p id="viewError" class="error"></p><button class="btn" data-route="today">Volver al inicio</button></section>';
    document.querySelector('#viewError').textContent = error instanceof Error ? error.message : String(error);
    bind();
  }
}

window.addEventListener('hashchange', render);
window.addEventListener('routechange', render);
render();
