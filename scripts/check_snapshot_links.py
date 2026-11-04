from academic_workspace.live_browser import LiveBrowserTransport
from academic_workspace.browser_source import BrowserApiCollector
with LiveBrowserTransport() as t:
    s=BrowserApiCollector(t).collect()
    for a in s.activities:
        if a.course_id == '_8208_1' and a.title in {'Aspectos de nueva Visión','Determinación de la Interacción','Aspectos de Interacción e Interdependencia','Introducción Tendencias Administrativas Modernas'}:
            print(a.title, repr(a.body))
