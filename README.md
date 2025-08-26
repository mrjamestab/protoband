# Protoboard Viewer

Visualiza el estado de conexiones de un protoboard a partir de un archivo de texto.

## Requisitos
- Python 3.x
- No requiere dependencias externas (usa solo la librería estándar)

## Uso

1. Coloca tu archivo de conexiones (por ejemplo, `conexiones.txt`) en la misma carpeta que el script.
2. Ejecuta el siguiente comando en la terminal:

```bash
python protoband_app.py conexiones.txt
```

Opcionalmente, puedes indicar el número de filas a mostrar (por defecto son 30):

```bash
python protoband_app.py conexiones.txt 40
```

## Notas
- El archivo `conexiones.txt` debe tener el formato esperado por la app (ver comentarios en el código para detalles).
- La ventana se actualizará automáticamente si el archivo cambia.
