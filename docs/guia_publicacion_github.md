# Guía de publicación en GitHub

El contenido del ZIP es un repositorio ya organizado. **No subas el ZIP como archivo único** si quieres que GitHub muestre el notebook y el README; hay que descomprimirlo y publicar los archivos.

## Método recomendado: GitHub Desktop (Windows)

1. Descarga y descomprime `Pronostico_Demanda_Materiales_RF30_GitHub.zip` en una carpeta de tu PC.
2. Instala **GitHub Desktop** desde su web oficial y accede a tu cuenta.
3. En GitHub Desktop selecciona **File > Add local repository**. Escoge la carpeta descomprimida. Si aparece que no es un repositorio, pulsa **Create a repository here**.
4. Escribe una descripción, deja visible sólo el contenido académico y crea el repositorio local.
5. Selecciona **Publish repository**, define el nombre `Pronostico_Demanda_Materiales_RF30` y decide si será **Private** o **Public**.
6. Antes de publicar en modo público, revisa la lista de archivos. Deben aparecer sólo `README.md`, notebooks, módulos, documentos, tests, CSV ficticio y gráficos demostrativos. **Nunca** `Jobs*.csv`, un Excel real o la tesis completa con información sensible.
7. Publica. Abre el repositorio en GitHub y comprueba que el README y el notebook se vean correctamente.

## Alternativa: terminal Git

Desde la carpeta descomprimida y con un repositorio **vacío** ya creado en GitHub (sin README inicial):

```bash
git init
git branch -M main
git add .
git status
git commit -m "Proyecto academico: pronostico de materiales RF30"
git remote add origin https://github.com/TU_USUARIO/Pronostico_Demanda_Materiales_RF30.git
git push -u origin main
```

Reemplaza `TU_USUARIO`. Debes iniciar sesión cuando GitHub lo solicite. `git status` es la revisión indispensable antes del commit.

## Verificación técnica

Para comprobar el proyecto localmente:

```bash
pip install -e ".[dev]"
python -m pytest -q
python -m material_forecasting.cli
```

Los CSV de resultados generados en `outputs/` no entran al repositorio por la configuración de `.gitignore`.
