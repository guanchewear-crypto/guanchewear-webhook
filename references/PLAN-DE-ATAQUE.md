# 🇮🇨 PLAN DE ATAQUE: GuancheWear

## Objetivo: 3.000€/mes beneficio con camisetas(25€) y sudaderas(35€) personalizadas por IA

---

## 🎯 DIAGNÓSTICO ACTUAL

| Aspecto | Estado | Detalle |
|---------|--------|---------|
| **Hosting** | ✅ | Hostinger PHP 8.3, 1536MB, OPcache |
| **WordPress** | ✅ | Instalado, Kadence Theme activo |
| **Plugins** | ✅ | WooCommerce, Stripe, Yoast, LiteSpeed, Printify, EWWW, Wordfence, WP Mail SMTP |
| **Webhook IA** | ✅ | Desplegado en https://guanchewear-webhook.vercel.app |
| **Stripe** | ✅ | Keys configuradas, webhook creado |
| **Printify** | ✅ | Shop 28377075, TSM-EU, variantes OK |
| **Página /crear** | ⚠️ | Creada pero solo iframe negro (sin diseño) |
| **Landing page** | ❌ | Tema Kadence default, sin contenido |
| **WooCommerce** | ⚠️ | Instalado pero no configurado (envíos, impuestos, productos) |
| **OpenAI** | ❌ | API key válida pero sin créditos |
| **Productos** | ❌ | No creados en WooCommerce |

---

## 📋 FASES DE EJECUCIÓN

### FASE 0: Recargar OpenAI ← **AHORA MISMO**
```
1. Ve a https://platform.openai.com/settings/organization/billing
2. Añade 10€ de saldo
   └── Coste por diseño: ~$0.04 (GPT-4o-mini) + $0.08 (DALL-E 3) = ~$0.12/diseño
   └── 10€ ≈ 100 diseños generados
3. Dime cuando esté listo para probar
```

---

### FASE A: DISEÑAR LA WEB COMPLETA (Prioridad #1)

#### A1. Landing page (guanchewear.es/)
Diseño dark mode premium con:

```
┌─────────────────────────────────────────────┐
│ GUANCHEWEAR          Inicio | Crear | Tienda │
├─────────────────────────────────────────────┤
│                                               │
│     ✨ "TU IDEA. TU DISEÑO."                  │
│     Describe tu idea y la IA la convierte     │
│     en arte textil. En 2 minutos.             │
│                                               │
│     [ CREA TU DISEÑO ÚNICO ]                  │
│                                               │
│     ⭐ 4.9/5 · Envío 2-4 días · 100% único   │
│                                               │
├─────────────────────────────────────────────┤
│  CÓMO FUNCIONA                               │
│                                               │
│  ① Elige tu prenda     ② Describe tu idea    │
│  ③ IA diseña          ④ Confirmas y pagas    │
│                                               │
├─────────────────────────────────────────────┤
│  GALERÍA DE DISEÑOS                          │
│  [Mockups de ejemplo generados por IA]       │
│                                               │
├─────────────────────────────────────────────┤
│  Lo dicen nuestros clientes                  │
│  "Nunca pensé que podría tener un diseño     │
│   tan original" ⭐⭐⭐⭐⭐                       │
│                                               │
├─────────────────────────────────────────────┤
│  Newsletter + Footer                         │
└─────────────────────────────────────────────┘
```

**Implementación:**
- Página completa HTML/CSS inline en WordPress
- Inspirada en Linear + Stripe + Apple (dark mode)
- Animaciones sutiles, responsive, mobile-first
- Colores: #0A0A0A fondo, #D4A853 dorado acento, #F5F5F5 texto

#### A2. Página /crear (la experiencia de diseño)
Actualmente: iframe al webhook → negro sin contenido porque OpenAI no tiene créditos.

**Cuando OpenAI esté activo:**
El flujo es:
```
① Selector: Camiseta(25€) / Sudadera(35€) + TALLA + COLOR
② Input: "Describe tu diseño ideal..."
③ Botón: ✨ GENERAR
④ Loading: "Nuestro artista IA está trabajando..."
⑤ Aparecen 2 diseños únicos en mockups fotorrealistas
⑥ Cliente elige → Confirma → Stripe pago → Printify produce
```

**Mientras OpenAI no tiene créditos:**
Mostrar una versión DEMO con imágenes de ejemplo para que el cliente vea cómo funciona.

#### A3. Páginas secundarias
- `/como-funciona` → Explicación del proceso
- `/faq` → Preguntas frecuentes
- `/contacto` → Formulario de contacto
- `/galeria` → Galería de diseños de clientes (futuro)

---

### FASE B: CONFIGURAR WOOCOMMERCE

#### B1. Envíos
- España peninsular: 4.99€ tarifa plana
- Canarias: 9.99€
- Gratis desde 50€

#### B2. Impuestos
- IVA 21% para España peninsular
- IGIC 7% para Canarias

#### B3. Productos
- Crear "Camiseta personalizada" (25€) como producto simple
- Crear "Sudadera personalizada" (35€) como producto simple
- Ambos con atributos: Talla (S-XXL), Color (Negro, Blanco, Azul marino, Gris)
- Conectar con Printify (automatic fulfillment)

#### B4. Stripe
- Activar Stripe como método de pago
- Modo live (ya tenemos keys)
- Apple Pay + Google Pay

---

### FASE C: SEO + RENDIMIENTO

#### C1. Yoast SEO
- Configurar sitemap XML
- Meta tags para cada página
- Schema markup (Organization, Product, FAQ)
- Google Search Console

#### C2. LiteSpeed Cache
- Habilitar page cache
- CSS minify + combine
- JS defer
- WebP conversion automática
- Lazy load imágenes

#### C3. EWWW Image Optimizer
- Comprimir todas las imágenes
- Convertir a WebP automáticamente

---

### FASE D: LANZAMIENTO

1. Probar flujo completo (diseño → pago → producción)
2. Lighthouse audit (>90)
3. Heatmaps (Microsoft Clarity)
4. Campaña redes sociales
5. Monitorear y ajustar

---

## 📊 TIMELINE (orden de ejecución)

```
SEMANA 1:
  LUN: ✅ [AHORA] Recargar OpenAI + diseñar landing page
  MAR: 🎨 Landing page terminada + página /crear mejorada
  MIE: 🛒 WooCommerce configurado (envíos, impuestos, productos)
  JUE: 🔌 Probar flujo completo (si OpenAI recargado)
  VIE: ⚡ SEO + rendimiento + cache
  
SEMANA 2:
  LUN: 🧪 Tests A/B + heatmaps
  MAR: 📱 Campaña redes sociales
  MIE: 🚀 LANZAMIENTO OFICIAL
```

---

## 🔑 LO QUE NECESITO DE TI AHORA

| Prioridad | Qué necesito | Para qué |
|-----------|-------------|----------|
| 🔴 **AHORA** | Recargar OpenAI (10€) | Activar generación de diseños |
| 🟡 Hoy | Confirmar paleta de colores y estilo | Diseñar la web |
| 🟢 Esta semana | Acceso a redes sociales (opcional) | Campaña lanzamiento |

**¿Empezamos con lo más urgente: recargar OpenAI y diseñar la landing page?** 🚀
