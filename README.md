# movlog

## Inicio rápido

1. Abre el Codespace y espera ~8 minutos a que se construya el entorno
2. Cuando estés en el terminal limpio de /workspaces/movlog(main) ejecuta:
```bash
bash .devcontainer/start.sh
```
3. Espera hasta que veas un mensaje que indique `✔ TODO OK ✔`
4. Ejecuta `start_movlog` y ve configurando las API Key del `.env` en el orden que se van pidiendo (indicaciones para conseguirlas en `/docs/api_key_guide.md`)
5. Revisa que todo haya ido `✅ OK` y accede a la URL de la UI indicada por consola

## Soluciones de errores

- **`start_movlog` da problemas:** Escribe `source ~/.bashrc && start_movlog` en el terminal.

- **Entorno roto tras `start_movlog`:** Borra el Codespace actual y crea uno nuevo.

- **Fallos puntuales o servicios caídos:** Ejecuta `reset_all` para reiniciar todos los servicios sin tocar los datos. Si el problema persiste, borra el Codespace y crea uno nuevo.

- **API /docs (Swagger) no carga:** Comprueba que la URL termine en `/docs`.

- **La UI de Langfuse me da problemas** Comprueba que la URL sea correcta (`https://{CODESPACE_NAME}-13000.app.github.dev`).