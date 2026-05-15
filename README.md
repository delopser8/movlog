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
6. Elige si vas a usar datos simulados (mock data) o empezar de cero con el flujo normal de Movlog
7. Revisa que todo haya ido `✅ OK` y accede a la URL indicada por consola

## Soluciones de errores

- **Entorno roto tras `start_movlog`:** Borra el Codespace actual y crea uno nuevo.

- **Fallos puntuales o servicios caídos:** Ejecuta `reset_all` para reiniciar todos los servicios sin tocar los datos. Si el problema persiste, borra el Codespace y crea uno nuevo.

- **API /docs (Swagger) no carga:** Comprueba que la URL termine en `/docs`.

- **La UI de Langfuse me da problemas** Comprueba que la URL sea correcta (`https://{CODESPACE_NAME}-13000.app.github.dev`).