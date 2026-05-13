# movlog

## Inicio rápido

1. Abre el Codespace y espera ~8 minutos a que se construya el entorno
2. Abre el terminal y ejecuta:
```bash
bash .devcontainer/start.sh
```
3. Cuando veas al final `✔ TODO OK ✔` el entorno está listo
4. Configura tus API keys en `.env` siguiendo `/docs/api_key_guide.md`
5. Ejecuta `start_movlog` para iniciar la aplicación

## Soluciones de errores

- **Entorno roto tras `start_movlog`:** Borra el Codespace actual y crea uno nuevo.

- **API /docs (Swagger) no carga:** Comprueba que la URL termine en `/docs`.

- **Servicio caído o UI/API sin respuesta:** Ejecuta `reset_all` en el terminal para reiniciar todos los servicios sin tocar los datos.