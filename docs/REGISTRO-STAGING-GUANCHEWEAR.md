# Registro de actualizaciones de staging — GuancheWear

Usar una entrada por cambio. No incluir contraseñas, tokens, `.env`, datos de
clientes ni volcados de base de datos.

## YYYY-MM-DD HH:MM — Título del cambio

- Entorno: local / staging remoto
- URL:
- Responsable:
- Backup previo: generación + SHA256 / ubicación
- Commit frontend:
- Commit backend:
- Motivo:
- Archivos o componentes modificados:
- Base de datos modificada: sí / no
- Comandos ejecutados:
- Verificación técnica:
  - [ ] `npm run verify`
  - [ ] Homepage devuelve HTTP 200
  - [ ] `/diseno/` carga
  - [ ] `/wp-admin/` carga
  - [ ] Imágenes y assets cargan
  - [ ] WooCommerce funciona
  - [ ] Formularios y WhatsApp funcionan
  - [ ] Consola del navegador sin errores nuevos
  - [ ] No existe overflow horizontal
- Resultado: pendiente / aprobado / revertido
- Rollback:
- Observaciones:

## Regla de promoción

No modificar `guanchewear.es` hasta que el staging haya sido validado y exista:

1. backup previo restaurable;
2. commit o snapshot identificado;
3. comprobación funcional de WordPress, WooCommerce, imágenes y formularios;
4. rollback documentado;
5. aprobación explícita.

## 2026-09-18 — Atmósfera dorada y corrección de colecciones

- Entorno: local (`http://127.0.0.1:5174/`)
- Backup previo: `2026-09-17_223627`, verificado y disponible en tres nubes.
- Commit frontend: `3a982d6`.
- Commit backend de código: `f2b7590`; el puntero del submódulo se actualiza en
  este checkpoint de GitHub.
- Base de datos modificada: no.
- Archivos: `src/App.tsx`, `src/index.css`,
  `src/components/ParticleField.tsx`.
- Cambio: atmósfera Canvas 2D dorada visible desde colecciones y restauración del
  `position: sticky` que evitaba el hueco negro antes de «Nuestro método».
- Verificación: `npm run verify` exit 0; lint/build y verificadores de catálogo,
  anclas, pedidos, importador, mapa y galería correctos; sin overflow horizontal.
- Resultado: aprobado en local; pendiente de validar en staging remoto.
- Producción: no modificada.
- Rollback: restaurar el commit anterior del submódulo y el puntero del backend.

## Estado inicial — 2026-09-18

- Staging remoto: pendiente de elegir servidor y dominio.
- Producción: no modificada.
- Backup de referencia: `2026-09-17_223627`.
- Próximo paso: desplegar el maestro WordPress y el SQL en un staging aislado.
