/**
 * TDS -- Territorios de Desenvolvimento Social
 * Vue Router Plugin: injects TDS hero banner into /courses page.
 *
 * Strategy:
 *   - Uses Vue's app.mixin + router.afterEach to detect /courses route.
 *   - Injects the hero as a plain DOM element into the first .p-5 container.
 *   - No Vue component dependencies -- pure DOM manipulation.
 *   - If upstream renames classes/routes, the hero simply does not appear
 *     (fails silently, never breaks rendering).
 *
 * Installed via a single `sed` patch in main.js:
 *   import { tdsPlugin } from './tdsPlugin'
 *   app.use(tdsPlugin)
 */

const HERO_ID = 'tds-hero-banner'

const HERO_HTML = `
<div id="${HERO_ID}" class="tds-hero">
  <div class="tds-hero__content">
    <img
      src="/files/logos_act/tds_main.png"
      alt="TDS"
      class="tds-hero__logo"
      onerror="this.style.display='none'"
    />
    <h1 class="tds-hero__title">
      Territ&oacute;rios de Desenvolvimento<br />Social e Inclus&atilde;o Produtiva
    </h1>
    <p class="tds-hero__subtitle">
      Secretaria do Trabalho e Desenvolvimento Social &mdash; Tocantins
    </p>
    <p class="tds-hero__tagline">
      &ldquo;Aprenda no ritmo da sua vida, pelo WhatsApp ou pelo portal.&rdquo;
    </p>
    <div class="tds-hero__partners">
      <img src="/files/logos_act/ipex.png" alt="IPEX" class="tds-hero__partner-logo" onerror="this.style.display='none'" />
      <img src="/files/logos_act/uft.png"  alt="UFT"  class="tds-hero__partner-logo" onerror="this.style.display='none'" />
      <img src="/files/logos_act/fapt.png" alt="FAPT" class="tds-hero__partner-logo" onerror="this.style.display='none'" />
      <img src="/files/logos_act/cdr.png"  alt="CDR"  class="tds-hero__partner-logo" onerror="this.style.display='none'" />
    </div>
  </div>
  <div class="tds-hero__stats">
    <div class="tds-hero__stats-title">Sua Jornada</div>
    <div class="tds-hero__stat-row">
      <svg fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M12 6.253v13m0-13C10.832 5.477 9.246 5 7.5 5S4.168 5.477 3 6.253v13C4.168 18.477 5.754 18 7.5 18s3.332.477 4.5 1.253m0-13C13.168 5.477 14.754 5 16.5 5c1.747 0 3.332.477 4.5 1.253v13C19.832 18.477 18.247 18 16.5 18c-1.746 0-3.332.477-4.5 1.253"/></svg>
      <span>Trilhas dispon&iacute;veis</span>
      <span class="tds-hero__stat-value">5</span>
    </div>
    <div class="tds-hero__stat-row">
      <svg fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M12 8v4l3 3m6-3a9 9 0 11-18 0 9 9 0 0118 0z"/></svg>
      <span>60h por trilha</span>
    </div>
    <div class="tds-hero__stat-row">
      <svg fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M17 20h5v-2a3 3 0 00-5.356-1.857M17 20H7m10 0v-2c0-.656-.126-1.283-.356-1.857M7 20H2v-2a3 3 0 015.356-1.857M7 20v-2c0-.656.126-1.283.356-1.857m0 0a5.002 5.002 0 019.288 0M15 7a3 3 0 11-6 0 3 3 0 016 0z"/></svg>
      <span>Gratuito &middot; Cad&Uacute;nico</span>
    </div>
  </div>
</div>
`

function injectHero() {
  // Already injected
  if (document.getElementById(HERO_ID)) return

  // Find the content container on the courses page.
  // Upstream Frappe LMS uses a <div class="p-5 pb-10"> as the main
  // content area after the sticky header. We look for this pattern.
  const containers = document.querySelectorAll('.p-5.pb-10, .p-5')
  let target = null

  for (const el of containers) {
    // Heuristic: the courses page container is inside #app,
    // after a sticky header, and is not inside a modal.
    if (el.closest('.modal, [role="dialog"]')) continue
    // Must be visible and have reasonable size
    if (el.offsetHeight > 0) {
      target = el
      break
    }
  }

  if (!target) return

  const wrapper = document.createElement('div')
  wrapper.innerHTML = HERO_HTML.trim()
  const heroEl = wrapper.firstElementChild

  // Insert at the top of the content area
  target.insertBefore(heroEl, target.firstChild)
}

function removeHero() {
  const el = document.getElementById(HERO_ID)
  if (el) el.remove()
}

function isCoursesListPage() {
  const path = window.location.pathname
  // Match /courses or /lms/courses but not /courses/some-slug
  return /^\/(lms\/)?courses\/?$/.test(path)
}

export const tdsPlugin = {
  install(app) {
    const router = app.config.globalProperties.$router

    if (!router) {
      // Fallback: if router is not available yet, use a MutationObserver
      const observer = new MutationObserver(() => {
        if (isCoursesListPage()) {
          // Small delay to let Vue render
          setTimeout(injectHero, 150)
        } else {
          removeHero()
        }
      })
      observer.observe(document.body, { childList: true, subtree: true })
      return
    }

    router.afterEach((to) => {
      // Remove hero on every navigation first
      removeHero()

      // Check if we are on the courses list page
      const routeName = to.name || ''
      const routePath = to.path || ''

      const isCoursesList =
        routeName === 'Courses' ||
        routeName === 'courses' ||
        /^\/(lms\/)?courses\/?$/.test(routePath)

      if (isCoursesList) {
        // Wait for Vue to render the page content
        setTimeout(injectHero, 100)
        // Retry once more in case rendering is slow
        setTimeout(injectHero, 500)
      }
    })

    // Also handle initial page load
    if (isCoursesListPage()) {
      setTimeout(injectHero, 300)
      setTimeout(injectHero, 800)
    }
  },
}
