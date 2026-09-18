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

## Estado inicial — 2026-09-18

- Staging remoto: pendiente de elegir servidor y dominio.
- Producción: no modificada.
- Backup de referencia: `2026-09-17_223627`.
- Próximo paso: desplegar el maestro WordPress y el SQL en un staging aislado.
