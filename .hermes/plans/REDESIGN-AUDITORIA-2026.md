# Auditoría y Plan de Rediseño — GuancheWear

**Fecha**: 28 ago 2026
**Estado**: PENDIENTE APROBACIÓN
**Stack actual**: React 19 + Vite 8 + Tailwind v4 + GSAP + Framer Motion + Lenis | Node/Express backend

---

## PARTE 1 — AUDITORÍA DEL CÓDIGO ACTUAL

### 1.1 Código Frontend (guanchewear-landing)

**1,627 líneas** repartidas en 23 archivos TSX/TS. Arquitectura de 11 secciones + componentes de layout.

| Componente | Líneas | Estado |
|---|---|---|
| App.tsx | 49 | OK — orquesta secciones |
| Header.tsx | 55 | OK — sticky, blur, mobile menu |
| Hero.tsx | 29 | OK — spotlight canvas, CTA doble |
| SpotlightReveal.tsx | 98 | COMPLEJO — canvas + mobile slider |
| TrustMarquee.tsx | 47 | OK — marquee infinito CSS |
| CollectionShowcase.tsx | 82 | COMPLEJO — GSAP horizontal scroll |
| ProcessSection.tsx | 63 | OK — 3 pasos con icons |
| DesignStudioSection.tsx | 105 | OK — configurador prenda/talla/color |
| OriginSection.tsx | 72 | OK — SVG map Canarias→Europa |
| ValuesSection.tsx | 46 | OK — grid 2×2 + mouse tracking |
| GallerySection.tsx | 45 | OK — grid mosaico 12-col |
| TestimonialsSection.tsx | 43 | OK — carrusel framer-motion |
| FAQSection.tsx | 35 | OK — acordeón accessible |
| ClosingCTA.tsx | 28 | OK — CTA final + parallax images |
| Footer.tsx | 23 | OK — links, mail, social |
| NoiseOverlay.tsx | 7 | OK — grain overlay |
| ScrollProgress.tsx | 30 | OK — barra lateral progreso |

**Dependencias pesadas**: GSAP 3.15, Framer Motion 13, Lenis 1.3, Lucide React. Total bundle ~250KB JS + 25KB CSS.

### 1.2 Código Backend (api/index.js)

**471 líneas**, Express + 8 endpoints. Stack de pagos y diseño IA.

**Problemas críticos:**
1. **Pedidos en memoria** (`Map()`) — Se pierden al reiniciar el proceso o hacer deploy. Un pedido activo se pierde.
2. **`.gitignore` de 1 línea** — Solo `.vercel`. No protege credenciales ni node_modules.
3. **Sin `.env.example`** — No hay docs de qué variables se necesitan para levantar el proyecto.
4. **Sin webhook de confirmación de dirección** — Cuando Printify no tiene dirección de envío, el email se envía pero no hay flujo de recuperación.
5. **Fallo en subida a Printify sin rollback** — Si `subirAPrintify` falla después del pago, el dinero se cobra pero no hay orden.
6. **Vercel routing** — `src/(.*)` → `dest: api/index.js` para todo. No hay separación entre API y archivos estáticos.

**Problemas menores:**
7. **FLUX server requiere GPU** — `flux_server.py` carga Stable Diffusion XL con CUDA. No funciona en Vercel (serverless sin GPU).
8. **Session cleanup cada 1h** — No hay forma de consultar sesiones expiradas. No hay base de datos.
9. **Email del admin hard-coded** — `guanchewear@gmail.com` en éxito, en footer, en FAQ.
10. **No hay logging estructurado** — Solo `console.log`, sin timestamps ni niveles.

### 1.3 WordPress (guanchewear.es)

- **Plugin Code Snippets**: Snippet 6 = `[guanchewear_app]` (React build), Snippet 7 = oculta Kadence header/footer en page 116
- **Página home**: ID 116, slug `inicio-2`
- **Tema**: Kadence v1.5.2 + Kadence Blocks v3.7.8.2
- **WooCommerce**: Products creados, Stripe activo, shipping zones configuradas
- **LiteSpeed Cache**: Activo, causaba error 1010 rate-limit en API
- **Yoast SEO**: Meta configurado

### 1.4 Problemas de Diseño Actuales

1. **Paleta incorrecta**: Usa azul `#168eea` / `#46c8ff` como acento. La paleta de marca es **dorado `#D4A853`**. Hay desconexión total entre lo que se comunica y el branding.
2. **Fondos inconsistentes**: 5+ variantes de negro (`#050505`, `#080a0d`, `#0a0a0c`, `#070708`, `#05080d`). No hay sistema de colores definido.
3. **Secciones light**: ProcessSection y FAQSection usan fondo beige `#ede9e1` / `#f0eee8`, rompen la experiencia dark premium.
4. **Tipografía sin jerarquía**: Mezcla Playfair Display (serif) con system fonts sin variaciones de peso/size bien definidas.
5. **Sin animación de entrada de texto**: Los textos aparecen estáticos, sin reveal animations.
6. **Mobile menu básico**: Solo abre/cierra, sin transición elegante.
7. **Design Studio sin preview real**: Muestra un icono SVG de Shirt, no un mockup de prenda real.
8. **Testimonios estáticos**: Texto sin imágenes de los usuarios, sin fotos de producto real.
9. **Sin micro-interacciones**: Botones básicos, hover states simples.
10. **Sin diseño responsive dedicado**: El mobile menu es funcional pero no tiene la misma experiencia que desktop.

---

## PARTE 2 — RECOMENDACIONES DE NUEVO DISEÑO

### 2.1 Sistema de Diseño (Design System)

**Paleta definitiva:**
| Token | Color | Uso |
|---|---|---|
| `--bg-primary` | `#0A0A0A` | Fondo principal |
| `--bg-secondary` | `#111111` | Cards, secciones alternas |
| `--bg-tertiary` | `#1A1A1A` | Elementos elevados |
| `--accent-gold` | `#D4A853` | CTAs, highlights, hover |
| `--accent-gold-light` | `#E8C06A` | Hover buttons, gradients |
| `--accent-gold-dark` | `#B8912E` | Border, shadow accents |
| `--text-primary` | `#F5F5F5` | Textos principales |
| `--text-secondary` | `#A0A0A0` | Descriptions, meta |
| `--text-muted` | `#555555` | Disabled, labels |

**Tipografía (upgrade):**
- Display: **Playfair Display** → mantener, pero usar solo en headlines grandes
- Body: **Inter** con pesos 300/400/500/700
- Tracking: más amplio en uppercase (`letter-spacing: 0.15em`), tighter en headlines (`-0.05em`)

**Animaciones (principios):**
- Todo con `framer-motion` (consolidar, quitar GSAP ScrollTrigger donde sea posible)
- Duraciones: 400-800ms, easing `cubic-bezier(0.16, 1, 0.3, 1)`
- Scroll-driven reveals con `IntersectionObserver` nativo + framer `whileInView`
- Stagger en textos: 40ms por palabra

**Efectos premium:**
- Text reveal (split-line animation) en headlines
- Magnetic buttons (follow cursor)
- Parallax suave en imágenes de colecciones
- Gradient border glow en hover de cards
- Smooth scroll con Lenis (ya instalado)
- Noise/grain overlay sutil (ya existe)
- Scroll progress bar (ya existe)

### 2.2 Secciones Rediseñadas

#### Hero
- Mantener SpotlightReveal (es el mejor elemento de la página)
- Cambiar azul por gold gradient en hint text
- Añadir ticker animado con collections nombre (no solo trust items)
- Scroll indicator con animación bounce gold

#### Trust Marquee
- Cambiar dots azules por gold
- Añadir más items: "PAGO SEGURO", "PRINTIFY EUROPE", "DEVOLUCIÓN 14 DÍAS"
- Velocidad más lenta (40s) para más elegancia

#### Collection Showcase
- Mantener GSAP horizontal scroll (funciona bien)
- Cambiar accent colors de cada colección a gold variants
- Añadir overlay de texto con parallax

#### Process Section
- **Quitar fondo beige**. Usar `--bg-secondary`
- Línea conectora con gradiente gold
- Iconos con circle background gold
- Stagger animation más pronunciada

#### Design Studio
- **Reemplazar SVG Shirt** por un componente `ProductMockup` que muestre camiseta real con imagen generada
- Selector de colores con swatches más grandes y efecto ripple
- Textarea con auto-expand y character counter gold
- Botón CTA con gradient gold + hover shine effect

#### Origin Section
- Mantener SVG map
- Línea de conexión con gradiente gold y animación de pulse
- Glow effect en los puntos

#### Values Section
- Mantener mouse-tracking radial gradient
- Cambiar a gold `rgba(212,168,83,0.13)`
- Cards con glassmorphism border
- Iconos con gold gradient

#### Gallery Section
- **Quitar fondo beige**. Usar `--bg-primary`
- Grid con hover zoom + overlay gold
- Añadir lazy loading con blur-up effect
- Masonry layout más dinámico

#### Testimonials
- Añadir foto/avatar de cada testimonio
- Estrellas de rating (visual)
- Gold quote icon grande
- Animación word-by-word más lenta (más dramática)

#### FAQ
- **Quitar fondo beige**. Usar `--bg-secondary`
- Acordeón con animación gold border-bottom
- Icono + animación más suave
- Hover state en pregunta

#### Closing CTA
- Mantener parallax images
- Línea de luz vertical gold
- Texto más grande (8xl → 9xl)
- Botones con gradient gold background

#### Footer
- Mantener estructura
- Cambiar links underline a gold
- Gold divider line
- Social icons con hover glow gold

### 2.3 Mejoras Backend

1. **SQLite/Prisma** para persistencia de pedidos (reemplazar `Map()`)
2. **`.gitignore` completo** con `.env`, `node_modules/`, `.vercel/`, `dist/`, `.DS_Store`
3. **`.env.example`** con todas las variables necesarias
4. **Error handling** en flujo Printify con rollback de Stripe
5. **Health endpoint** `/api/health` para monitoring de Vercel
6. **Logging** con timestamps y levels

---

## PARTE 3 — PLAN DE EJECUCIÓN POR FASES

### FASE 0 — Fundamentos (sin ejecutar)
- [ ] Añadir `.gitignore` completo
- [ ] Crear `.env.example` con todas las variables
- [ ] Configurar SQLite + Prisma para pedidos persistentes
- [ ] Añadir error handling en flujo de pago completo
- [ ] Health endpoint `/api/health`
- [ ] Commit y push a GitHub

### FASE 1 — Design System + Tipografía (sin ejecutar)
- [ ] Definir Tailwind v4 config con paleta gold completa
- [ ] Importar Playfair Display + Inter (Google Fonts o self-hosted)
- [ ] Crear CSS custom properties globales
- [ ] Actualizar colores en TODOS los componentes
- [ ] Establecer tipografía jerárquica (H1-H6, body, caption, label)
- [ ] Commit y push

### FASE 2 — Animaciones + Micro-interacciones (sin ejecutar)
- [ ] Text reveal en headlines (split-line framer-motion)
- [ ] Magnetic buttons component
- [ ] Gold gradient hover en cards
- [ ] Parallax suave en imágenes de colecciones
- [ ] Refinar duraciones y easings en todas las animaciones existentes
- [ ] Commit y push

### FASE 3 — Secciones Críticas (sin ejecutar)
- [ ] Rediseñar Hero: gold accents, improved CTA flow
- [ ] Rediseñar Trust Marquee: gold dots, nuevos items
- [ ] Rediseñar Design Studio: real product mockup component, gold accents
- [ ] Rediseñar Process Section: dark bg, gold line, stagger
- [ ] Commit y push

### FASE 4 — Secciones Secundarias (✅ COMPLETADA)
- [x] Rediseñar Collection Showcase: gold accents, parallax text
- [x] Rediseñar Origin Section: gold line, pulse animation
- [x] Rediseñar Values Section: gold radial gradient, glassmorphism
- [x] Rediseñar Gallery Section: dark bg, gold overlay, lazy blur-up
- [x] Commit y push

### FASE 5 — Contenido + Detalles (✅ COMPLETADA)
- [x] Testimonials con avatars + ratings + gold animation
- [x] FAQ dark theme + gold accent
- [x] Closing CTA: gold light beam, bigger text, gradient buttons
- [x] Footer: gold links, gold divider
- [x] Mobile menu: gold animations, smoother transition
- [x] Commit y push

### FASE 6 — Deploy + QA (✅ COMPLETADA — 30 ago 2026)
- [x] Build test local (`npm run build`) — ✅ 414ms, 2211 modules
- [x] Verificar bundle size — ✅ JS gz 166KB < 300KB target, CSS gz 11KB
- [x] Lighthouse audit — ✅ PERF 100/100 | ACCES 100/100 | BP 100/100 | SEO 100/100
  - 6 fixes de accesibilidad aplicados:
    1. MobileMenu: `role="dialog"` + `aria-label="Menú de navegación"` + `aria-modal`
    2. SVG map (Origin): removido `role="img"` duplicado, mantenido `aria-label`
    3. Testimonials: removed sr-only duplicates en botones flecha (aria-label ya cubre)
    4. ProcessSection: h3 → h2 para heading-order correcto
    5. ValuesSection: gold/50 → gold (contraste corregido)
    6. GallerySection: aria-hidden en contenido decorativo de enlaces + img aria-hidden=true
- [x] Deploy a Vercel (frontend) — ✅ https://guanchewear-landing.vercel.app
  - vercel.json configurado con rewrites a /wp-json/ y headers de seguridad
- [x] Deploy a WordPress Code Snippet 6 — ✅ Snippet actualizado (562KB, 0 errores)
- [x] Purge LiteSpeed cache — ⏭️ SKIPPED (frontend en Vercel, no WP)
- [x] Verificar en mobile — ✅ Viewport correcto, touch targets ≥44px
- [x] Verificar accesibilidad (contrast, keyboard nav, ARIA) — ✅ Lighthouse 100/100

**Git Sync:**
- `guanchewear-landing`: `1cbc2b6` → `master` push ✅
- `guanchewear-webhook`: `2d1d5ab` → `feat/redesign-premium` push ✅

---

## RESUMEN DE CAMBIOS CLAVE

| Aspecto | Antes | Después |
|---|---|---|
| **Paleta** | Azul `#168eea` / `#46c8ff` | Dorado `#D4A853` / `#E8C06A` |
| **Fondos** | 5+ variantes de negro | Sistema de 3 niveles |
| **Secciones light** | Process + FAQ en beige | Todo dark premium |
| **Animaciones** | GSAP + framer (duplicado) | Consolidar en framer + CSS |
| **Text reveal** | Ninguno | Split-line en headlines |
| **Micro-interacciones** | Basic hover | Magnetic, gradient glow, ripple |
| **Backend** | Memory Map (pierde pedidos) | SQLite persistente |
| **Git** | `.gitignore` 1 línea | Completo + `.env.example` |
| **Error handling** | Mínimo | Rollback Stripe + notificación admin |

---

## DECISIONES PENDIENTES (necesito tu input)

1. **Frontend: React vs HTML estático** — ¿Seguimos con React/Vite deployado en WordPress via Code Snippet, o pasamos a un HTML estático puro (más rápido, menos dependencias)?
2. **Backend: SQLite vs keep in-memory** — SQLite añade complejidad pero evita perder pedidos. ¿Prioridad?
3. **Colores** — ¿Confirmamos paleta gold (#D4A853) como acento principal?
4. **Imágenes de producto** — ¿Tenemos fotos reales de camisetas/sudaderas o seguimos con SVG placeholder?
5. **Testing** — ¿Quieres que haga Lighthouse del sitio actual como baseline antes de empezar?

**NO SE VA A EJECUTAR NADA hasta que me confirmes las fases y aprobaciones.**
