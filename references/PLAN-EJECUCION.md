# 📋 PLAN DE EJECUCIÓN: Web primero, IA después

## 🟢 FASE 1: Web + Productos (AHORA)
Construir la tienda completa sin IA, funcionando con productos reales.

| Paso | Tarea | Tiempo |
|------|-------|--------|
| 1.1 | Obtener variant IDs de Printify (ropa) | 30min |
| 1.2 | Configurar WooCommerce: Moneda EUR, España, impuestos, envíos | 30min |
| 1.3 | Conectar Stripe en WooCommerce + modo live | 15min |
| 1.4 | Crear productos en WooCommerce (cada uno con su precio) | 1h |
| 1.5 | Página catálogo con todos los productos | 1h |
| 1.6 | Conectar WordPress a Vercel webhook (básico) | 30min |
| 1.7 | SEO (Yoast), Cache (LiteSpeed), Imágenes (EWWW) | 30min |

## 🔵 FASE 2: IA de Diseño (DESPUÉS)
Cuando la web esté sólida, diseñamos el sistema de IA.

| Paso | Tarea |
|------|-------|
| 2.1 | Investigar técnicas avanzadas para diseños textiles con SDXL |
| 2.2 | Crear prompts base que garanticen calidad |
| 2.3 | Probar distintos estilos (minimalista, detallado, abstracto) |
| 2.4 | Ajustar generación para mockups realistas |
| 2.5 | Probar flujo completo offline |
| 2.6 | Integrar con web + WooCommerce |

---

## 🎯 Catálogo de ropa definitivo

### CAMISETAS
| Producto | Printify Blueprint | Proveedor EU | Precio |
|----------|-------------------|--------------|--------|
| Gildan Heavy Cotton | 6 | TSM-EU (26) | 25€ |
| Gildan Softstyle | 12 | TSM-EU (26) | 28€ |
| Next Level 3600 Premium | 5 | TSM-EU (26) | 30€ |
| Unisex Boxy Tee | 437 | TSM-EU (26) | 32€ |
| Women's Favorite Tee | 9 | TSM-EU (26) | 28€ |

### SUDADERAS
| Producto | Printify Blueprint | Proveedor EU | Precio |
|----------|-------------------|--------------|--------|
| Gildan Heavy Blend Hoodie | 77 | TSM-EU (26) | 35€ |
| Gildan Full Zip Hoodie | 66 | TSM-EU (26) | 40€ |
| Gildan Crewneck Sweatshirt | 49 | TSM-EU (26) | 33€ |

### GORRAS Y BOLSAS
| Producto | Printify Blueprint | Proveedor EU | Precio |
|----------|-------------------|--------------|--------|
| Gorra ajustable | Buscar | TSM-EU | 18€ |
| Bolsa de tela | Buscar | TSM-EU | 14€ |

---

## 📐 Flujo final (post-IA)

```
Catálogo → Elige producto + talla + color
         → Describe diseño
         → GPT-4o-mini + metadatos del producto
         → SDXL local (tu PC) genera 2 diseños
         → Confirmas → Pagas → Printify produce
```

**¿Confirmo este plan y empiezo por el paso 1.1?** 🔨