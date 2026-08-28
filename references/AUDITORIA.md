# 🇮🇨 AUDITORÍA COMPLETA: GuancheWear

## Estado actual (todo verificado)

### 🟢 FUNCIONANDO CORRECTAMENTE

| Componente | Estado | Detalle |
|-----------|--------|---------|
| **Webhook Vercel** | ✅ | https://guanchewear-webhook.vercel.app - 8 endpoints |
| **Landing page** | ✅ | https://guanchewear.es/ - Hero, galería, testimonios |
| **Página /crear** | ✅ | https://guanchewear.es/crear/ - Diseñador IA |
| **Generación IA** | ✅ | GPT-4o-mini refina + SDXL local genera imágenes |
| **SDXL Local** | ✅ | Puerto 8010, RTX 4070 12GB |
| **Túnel localtunnel** | ✅ | https://guanchewear-flux.loca.lt |
| **Stripe** | ✅ | Keys configuradas, webhook creado |
| **Printify** | ✅ | Shop activo, TSM-EU conectado |
| **WordPress** | ✅ | Kadence theme, 8 plugins activos |
| **Hostinger** | ✅ | PHP 8.3, 1536MB, OPcache |

### 🟡 FUNCIONA PERO HAY QUE MEJORAR

| Componente | Problema | Solución |
|-----------|----------|----------|
| **Landing page** | Sin imágenes reales (solo emojis) | Subir mockups reales de producto |
| **Página /crear** | Dentro de iframe en WordPress | Convertir a página nativa o mejorar integración |
| **SDXL Server** | Hay que iniciarlo manualmente | Crear script .bat que arranque todo |
| **Túnel** | Hay que iniciarlo manualmente | Incluir en mismo script .bat |

### 🔴 NO FUNCIONA / NO EXISTE

| Componente | Estado | Prioridad |
|-----------|--------|-----------|
| **WooCommerce productos** | ❌ No creados | 🔴 Alta |
| **WooCommerce envíos** | ❌ No configurados | 🔴 Alta |
| **WooCommerce impuestos** | ❌ No configurados | 🟡 Media |
| **Stripe en WooCommerce** | ❌ No conectado | 🔴 Alta |
| **Página /como-funciona** | ❌ No creada | 🟡 Media |
| **Página /faq** | ❌ No creada | 🟢 Baja |
| **Página /contacto** | ❌ No creada | 🟢 Baja |
| **Yoast SEO** | ❌ No configurado | 🟡 Media |
| **LiteSpeed Cache** | ❌ No optimizado | 🟡 Media |
| **EWWW Images** | ❌ No configurado | 🟢 Baja |
| **Google Search Console** | ❌ No conectado | 🟢 Baja |
| **WooCommerce REST API keys** | ❌ No generadas | 🔴 Alta |
| **Flujo completo: diseño→pago** | ❌ No probado | 🔴 Alta |
| **SDXL auto-inicio** | ❌ Script no creado | 🟡 Media |

---

## 📋 PLAN DE ACCIÓN PRIORIZADO

### PRIORIDAD 1: WooCommerce (lo mínimo para vender)

```
[ ] 1.1 Crear WooCommerce API keys (para conectar webhook)
[ ] 1.2 Configurar Stripe en WooCommerce
[ ] 1.3 Crear zonas de envío (España peninsular 5€, Canarias 10€, gratis +50€)
[ ] 1.4 Configurar impuestos (IVA 21%, IGIC 7%)
[ ] 1.5 Crear productos:
     - Camiseta personalizada 25€ (atributos: talla S-XXL, color)
     - Sudadera personalizada 35€ (atributos: talla S-XXL, color)
[ ] 1.6 Conectar Printify fulfillment automático
```

### PRIORIDAD 2: Contenido y páginas

```
[ ] 2.1 Crear página /como-funciona (explicación del proceso IA)
[ ] 2.2 Subir mockups reales a la landing page
[ ] 2.3 Mejorar integración /crear (iframe → nativo)
[ ] 2.4 Crear página /faq
```

### PRIORIDAD 3: SEO y rendimiento

```
[ ] 3.1 Configurar Yoast SEO (sitemap, meta tags, schema)
[ ] 3.2 Activar LiteSpeed Cache (page cache, minify, lazy load)
[ ] 3.3 EWWW Image Optimizer (WebP automático)
[ ] 3.4 Google Search Console
```

### PRIORIDAD 4: Infraestructura

```
[ ] 4.1 Crear script inicio_rapido.bat (arranca SDXL + túnel)
[ ] 4.2 Probar flujo completo: diseño → pago → Printify
[ ] 4.3 Configurar monitoring (qué pasa si el servidor local cae)
```

---

## 💰 ECONOMÍA DEL PROYECTO

| Concepto | Coste |
|----------|-------|
| **Hostinger** | ~10€/mes |
| **OpenAI (GPT-4o-mini)** | ~0.02¢/diseño |
| **SDXL (tu GPU)** | 0€ (gratis) |
| **Stripe fees** | 1.4% + 0.25€ por venta |
| **Printify camiseta** | ~8€ producción |
| **Printify sudadera** | ~15€ producción |
| **Vercel** | 0€ (hobby) |
| **Total por camiseta** | ~8.60€ coste → 25€ venta = **16.40€ margen** |
| **Total por sudadera** | ~15.60€ coste → 35€ venta = **19.40€ margen** |

### Para 3.000€/mes beneficio:
→ **~170 camisetas** o **~155 sudaderas** al mes (6-7 al día)