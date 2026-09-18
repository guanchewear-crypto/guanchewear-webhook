# Estado de GuancheWear — 2026-09-18

Documento de estado versionable y sanitizado. No contiene credenciales, `.env`,
volcados de base de datos, passphrases ni backups cifrados.

## Repositorios de código

| Componente | Repositorio | Rama | Commit verificado |
|---|---|---|---|
| Backend y tooling | `guanchewear-crypto/guanchewear-webhook` | `feat/redesign-premium` | `dea7333` |
| Landing React/Vite | `guanchewear-crypto/guanchewear-BACKUPS-WEB` | `master` | `7132bc7` |

El frontend está declarado como submódulo `guanchewear-landing` del backend.
Los dos commits coinciden con sus respectivos remotos de GitHub.

## Landing actual

- WordPress + WooCommerce + Kadence.
- React + Vite embebido en WordPress.
- Backend webhook en Python.
- Pagos mediante Stripe y fulfillment mediante Printify.
- 41 prendas: 18 camisetas y 23 sudaderas.
- 82 imágenes WebP reales con logo GW dorado.
- Galería con 16 fichas 4:3, dos por fila en desktop y sin celdas vacías.
- Mapa de origen con geometría real de Canarias y Europa.
- Identidad visual intacta: fondo `#0A0A0A`, dorado `#D4A853`, texto `#F5F5F5`.
- La animación de micro partículas doradas solicitada **todavía no está implementada**.
  La ejecución se interrumpió durante la inspección previa y no se modificó código
  de la landing para ese efecto.

## Staging

- Staging local histórico: `http://127.0.0.1:9400/`.
- Estudio de diseño: `http://127.0.0.1:9400/diseno/`.
- El servidor WordPress Playground no está ejecutándose actualmente.
- Staging remoto: pendiente de elegir servidor y dominio.
- Producción `guanchewear.es`: no modificada.

Cada cambio de staging debe registrarse con fecha, entorno, URL, backup previo,
commits, archivos modificados, pruebas, resultado y rollback. La plantilla operativa
está en `Registro de actualizaciones de staging GuancheWear.md` del vault local de
Obsidian.

## Backup y migración WordPress

Backup vigente: generación `2026-09-17_223627`, con 8 artefactos. Fue descifrado,
verificado por SHA256 y restaurado en un directorio temporal antes de darse por
válido. Las copias cifradas están destinadas a OneDrive, iCloud Drive y Google Drive.

El paquete local para migrar WordPress está preparado en:

```text
C:\Users\Usuario\Downloads\GuancheWear-migracion-2026-09-17\
```

Incluye, entre otros:

- `wordpress-database.sql`: base de datos portable WordPress/WooCommerce.
- `wordpress-master-site.zip`: sitio WordPress completo, plugins, tema, uploads y
  SQLite local.
- `wordpress-theme-source.zip`: fuentes y assets del tema.
- `wordpress-deploy-package.zip`: paquete del tema listo para desplegar.
- `README-MIGRACION.txt`: orden recomendado de importación.

Estos archivos contienen datos del sitio y no deben publicarse sin cifrar.
El repositorio no incluye el paquete, la base de datos, el `.env` ni la passphrase.

## Verificación

Frontend:

```bash
cd "C:/Users/Usuario/guanchewear-webhook/guanchewear-landing"
npm run verify
```

El último estado confirmado del frontend fue `npm run verify` con exit 0.

Backend/tooling:

```bash
cd "C:/Users/Usuario/guanchewear-webhook"
python scripts/verify-tooling.py
```

La recuperación se realiza con `scripts/restore-backup.py`: descifra en temporal,
comprueba SHA256 antes de extraer y se niega a continuar si el hash no coincide.

## Pendientes

- Elegir y crear el staging remoto.
- Migrar el SQL y el maestro WordPress en staging.
- Validar páginas, imágenes, WooCommerce, formularios y consola del navegador.
- Implementar únicamente la capa sutil de micro partículas, después de aprobar el
  staging y sin alterar estructura, tipografías, colores, tamaños ni composición.
- Pasar la passphrase a un gestor de contraseñas y eliminar su archivo local.
- Sustituir cualquier credencial histórica del remoto git por un credential helper.
