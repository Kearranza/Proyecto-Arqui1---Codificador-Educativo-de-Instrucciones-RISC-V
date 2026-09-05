#!/usr/bin/env python3
"""
Autoverificación de la herramienta contra un archivo de vectores.

Lee un archivo con líneas del formato "<instruccion> ; 0xHEX", invoca
./run.sh con cada instrucción, extrae la línea "HEX: 0x..." de su salida y
la compara contra la codificación esperada.

Uso:
    python3 tools/autocheck.py [ruta_vectores]

Termina con código 0 si todos los vectores coinciden, y 1 en caso contrario.
"""
import os
import re
import subprocess
import sys

RAIZ = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
VECTORES_POR_OMISION = os.path.join(RAIZ, "kit", "vectores_ejemplo.txt")
RUN_SH = os.path.join(RAIZ, "run.sh")

RE_HEX = re.compile(r"^HEX:\s*(0x[0-9a-fA-F]{8})\s*$", re.MULTILINE)


def leer_vectores(ruta):
    vectores = []
    with open(ruta, encoding="utf-8") as archivo:
        for numero, linea in enumerate(archivo, start=1):
            linea = linea.strip()
            if not linea or linea.startswith("#"):
                continue
            if ";" not in linea:
                print(f"Aviso: línea {numero} sin separador ';', se omite: {linea}",
                      file=sys.stderr)
                continue
            instruccion, esperado = linea.split(";", 1)
            vectores.append((numero, instruccion.strip(), esperado.strip().lower()))
    return vectores


def ejecutar(instruccion):
    """Invoca ./run.sh y devuelve (hex_obtenido, mensaje_error)."""
    proceso = subprocess.run(
        [RUN_SH, instruccion],
        capture_output=True, text=True,
    )
    if proceso.returncode != 0:
        detalle = proceso.stderr.strip() or f"código de salida {proceso.returncode}"
        return None, detalle
    coincidencia = RE_HEX.search(proceso.stdout)
    if not coincidencia:
        return None, "la salida no contiene una línea 'HEX: 0x........'"
    return coincidencia.group(1).lower(), None


def main():
    ruta = sys.argv[1] if len(sys.argv) > 1 else VECTORES_POR_OMISION
    if not os.path.isfile(ruta):
        print(f"No se encontró el archivo de vectores: {ruta}", file=sys.stderr)
        return 2

    if not os.access(RUN_SH, os.X_OK):
        print(f"'{RUN_SH}' no tiene permiso de ejecución.", file=sys.stderr)
        print("Algunos formatos de archivo (zip, ciertos clones) no conservan "
              "ese permiso. Restáurelo con:\n\n    chmod +x run.sh\n",
              file=sys.stderr)
        return 2

    vectores = leer_vectores(ruta)
    if not vectores:
        print("El archivo no contiene vectores.", file=sys.stderr)
        return 2

    ancho = max(len(instruccion) for _, instruccion, _ in vectores)
    fallos = []

    print(f"Verificando {len(vectores)} vectores de {os.path.relpath(ruta, RAIZ)}\n")
    for numero, instruccion, esperado in vectores:
        obtenido, error = ejecutar(instruccion)
        if error is not None:
            estado = f"ERROR  ({error})"
            fallos.append((numero, instruccion, esperado, error))
        elif obtenido == esperado:
            estado = "OK"
        else:
            estado = f"FALLA  esperado {esperado}, obtenido {obtenido}"
            fallos.append((numero, instruccion, esperado, obtenido))
        print(f"  {instruccion.ljust(ancho)}  {esperado}  {estado}")

    print()
    print(f"Resultado: {len(vectores) - len(fallos)}/{len(vectores)} correctos.")
    if fallos:
        print("\nVectores con discrepancia:")
        for numero, instruccion, esperado, obtenido in fallos:
            print(f"  línea {numero}: {instruccion} -> esperado {esperado}, "
                  f"obtenido {obtenido}")
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
