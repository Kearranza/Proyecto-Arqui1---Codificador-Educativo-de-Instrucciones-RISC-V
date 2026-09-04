#!/usr/bin/env python3
"""
Validación de la herramienta contra el toolchain oficial de RISC-V (rv32).

Para cada caso de casos_prueba.txt:
  1. Lo ensambla con el ensamblador oficial (-march=rv32i -mabi=ilp32).
  2. Obtiene la codificación de referencia con objdump -d.
  3. La compara contra la salida de ./run.sh.
  4. Escribe la tabla de evidencia en EVIDENCIA.md.

Uso:
    python3 tools/validar_toolchain.py [ruta_casos]

El prefijo del toolchain se detecta automáticamente. Si el suyo tiene otro
nombre, indíquelo con la variable de entorno RISCV_PREFIX, por ejemplo:

    RISCV_PREFIX=riscv64-unknown-elf- python3 tools/validar_toolchain.py

Nota sobre los saltos: en sintaxis GNU el tercer operando de beq/bne es una
dirección, no un desplazamiento. Para que el ensamblador produzca el
desplazamiento que la herramienta codifica, este script emite los saltos
como '.+N' / '.-N', donde '.' es la dirección de la propia instrucción.
"""
import os
import re
import shutil
import subprocess
import sys
import tempfile

RAIZ = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
CASOS_POR_OMISION = os.path.join(RAIZ, "casos_prueba.txt")
RUN_SH = os.path.join(RAIZ, "run.sh")
EVIDENCIA = os.path.join(RAIZ, "EVIDENCIA.md")

PREFIJOS_CANDIDATOS = [
    "riscv32-unknown-elf-",
    "riscv64-unknown-elf-",
    "riscv32-unknown-linux-gnu-",
    "riscv64-unknown-linux-gnu-",
    "riscv32-elf-",
    "riscv64-elf-",
    "riscv64-linux-gnu-",
    "riscv32-none-elf-",
]

RE_HEX_HERRAMIENTA = re.compile(r"^HEX:\s*(0x[0-9a-fA-F]{8})\s*$", re.MULTILINE)
RE_LINEA_OBJDUMP = re.compile(r"^\s*([0-9a-f]+):\s+([0-9a-f][0-9a-f ]*?)\s{2,}(.*)$")
RE_SALTO = re.compile(r"^\s*(beq|bne)\b(.*),\s*([+-]?\w+)\s*$", re.IGNORECASE)


def detectar_prefijo():
    """Devuelve el prefijo del toolchain, o None si no se encuentra."""
    entorno = os.environ.get("RISCV_PREFIX")
    if entorno:
        if shutil.which(entorno + "as") and shutil.which(entorno + "objdump"):
            return entorno
        print(f"RISCV_PREFIX={entorno} pero no se encontraron "
              f"{entorno}as y {entorno}objdump en el PATH.", file=sys.stderr)
        return None
    for prefijo in PREFIJOS_CANDIDATOS:
        if shutil.which(prefijo + "as") and shutil.which(prefijo + "objdump"):
            return prefijo
    return None


def leer_casos(ruta):
    casos = []
    with open(ruta, encoding="utf-8") as archivo:
        for linea in archivo:
            linea = linea.strip()
            if not linea or linea.startswith("#"):
                continue
            if ";" in linea:
                instruccion, escenario = linea.split(";", 1)
            else:
                instruccion, escenario = linea, ""
            casos.append((instruccion.strip(), escenario.strip()))
    return casos


def a_sintaxis_gnu(instruccion):
    """
    Convierte el desplazamiento numérico de un salto a la forma '.+N',
    que es como GNU as expresa un destino relativo a la instrucción actual.
    Las demás instrucciones se emiten sin cambios.
    """
    coincidencia = RE_SALTO.match(instruccion)
    if not coincidencia:
        return instruccion
    mnemonico, registros, desplazamiento = coincidencia.groups()
    try:
        valor = int(desplazamiento, 0)
    except ValueError:
        return instruccion
    return f"{mnemonico}{registros}, .{valor:+d}"


def ensamblar(prefijo, casos, directorio):
    """Ensambla todos los casos y devuelve la lista de palabras en hex."""
    ruta_s = os.path.join(directorio, "casos.s")
    ruta_o = os.path.join(directorio, "casos.o")

    with open(ruta_s, "w", encoding="utf-8") as archivo:
        archivo.write("    .text\n")
        archivo.write("    .option norvc\n")   # sin instrucciones comprimidas
        archivo.write("    .align 2\n")
        for instruccion, _ in casos:
            archivo.write("    " + a_sintaxis_gnu(instruccion) + "\n")

    resultado = subprocess.run(
        [prefijo + "as", "-march=rv32i", "-mabi=ilp32", "-o", ruta_o, ruta_s],
        capture_output=True, text=True,
    )
    if resultado.returncode != 0:
        print("Fallo al ensamblar con el toolchain oficial:", file=sys.stderr)
        print(resultado.stderr, file=sys.stderr)
        sys.exit(1)

    resultado = subprocess.run(
        [prefijo + "objdump", "-d", "-M", "numeric,no-aliases", ruta_o],
        capture_output=True, text=True,
    )
    if resultado.returncode != 0:
        print("Fallo al desensamblar con objdump:", file=sys.stderr)
        print(resultado.stderr, file=sys.stderr)
        sys.exit(1)

    palabras = []
    desensamblado = []
    for linea in resultado.stdout.splitlines():
        coincidencia = RE_LINEA_OBJDUMP.match(linea)
        if not coincidencia:
            continue
        _direccion, bytes_hex, texto = coincidencia.groups()
        bytes_hex = bytes_hex.strip()
        if " " in bytes_hex:
            # Formato byte a byte, en orden little-endian.
            octetos = bytes_hex.split()
            if len(octetos) != 4:
                continue
            palabra = "".join(reversed(octetos))
        else:
            if len(bytes_hex) != 8:
                continue
            palabra = bytes_hex
        palabras.append("0x" + palabra.lower())
        desensamblado.append(" ".join(texto.split()))

    return palabras, desensamblado


def ejecutar_herramienta(instruccion):
    proceso = subprocess.run([RUN_SH, instruccion], capture_output=True, text=True)
    if proceso.returncode != 0:
        return None, (proceso.stderr.strip() or
                      f"código de salida {proceso.returncode}")
    coincidencia = RE_HEX_HERRAMIENTA.search(proceso.stdout)
    if not coincidencia:
        return None, "la salida no contiene una línea 'HEX: 0x........'"
    return coincidencia.group(1).lower(), None


def escribir_evidencia(prefijo, filas, version_toolchain):
    coincidencias = sum(1 for fila in filas if fila["coincide"])
    total = len(filas)

    with open(EVIDENCIA, "w", encoding="utf-8") as archivo:
        archivo.write("# Evidencia de validación contra el toolchain oficial\n\n")
        archivo.write("Proyecto Individual — Codificador Educativo de "
                      "Instrucciones RISC-V\n")
        archivo.write("CE-4301 Arquitectura de Computadores I\n\n")
        archivo.write("Kevin Carranza Blanco — carné 2020163275\n")
        archivo.write("Instituto Tecnológico de Costa Rica\n\n")

        archivo.write("## Entorno de validación\n\n")
        archivo.write(f"- Prefijo del toolchain: `{prefijo}`\n")
        archivo.write(f"- Ensamblador: `{prefijo}as -march=rv32i -mabi=ilp32`\n")
        archivo.write(f"- Desensamblador: `{prefijo}objdump -d -M numeric,no-aliases`\n")
        if version_toolchain:
            archivo.write(f"- Versión reportada: `{version_toolchain}`\n")
        archivo.write("\nLos saltos condicionales se ensamblan como `.+N` / `.-N` "
                      "porque en sintaxis GNU el tercer operando de `beq`/`bne` es "
                      "una dirección, no un desplazamiento; `.` denota la dirección "
                      "de la propia instrucción, de modo que el desplazamiento "
                      "resultante es exactamente el que codifica la herramienta.\n\n")

        archivo.write("## Resultado global\n\n")
        archivo.write(f"**{coincidencias}/{total} casos coinciden.**\n\n")

        archivo.write("## Tabla comparativa\n\n")
        archivo.write("| # | Instrucción | Escenario | Modelo propio | objdump | "
                      "Desensamblado | Coincide |\n")
        archivo.write("|---|---|---|---|---|---|---|\n")
        for indice, fila in enumerate(filas, start=1):
            marca = "Sí" if fila["coincide"] else "**NO**"
            archivo.write(
                f"| {indice} | `{fila['instruccion']}` | {fila['escenario']} | "
                f"`{fila['modelo']}` | `{fila['referencia']}` | "
                f"`{fila['desensamblado']}` | {marca} |\n")
        archivo.write("\n")

        if coincidencias == total:
            archivo.write("Todos los casos de prueba producen la misma "
                          "codificación que el toolchain oficial.\n")
        else:
            archivo.write("### Casos con discrepancia\n\n")
            for indice, fila in enumerate(filas, start=1):
                if not fila["coincide"]:
                    archivo.write(f"- Caso {indice}: `{fila['instruccion']}` — "
                                  f"modelo `{fila['modelo']}`, referencia "
                                  f"`{fila['referencia']}`\n")


def main():
    ruta_casos = sys.argv[1] if len(sys.argv) > 1 else CASOS_POR_OMISION
    if not os.path.isfile(ruta_casos):
        print(f"No se encontró el archivo de casos: {ruta_casos}", file=sys.stderr)
        return 2

    if not os.access(RUN_SH, os.X_OK):
        print(f"'{RUN_SH}' no tiene permiso de ejecución.", file=sys.stderr)
        print("Restáurelo con:\n\n    chmod +x run.sh\n", file=sys.stderr)
        return 2

    prefijo = detectar_prefijo()
    if prefijo is None:
        print("No se encontró un toolchain de RISC-V en el PATH.", file=sys.stderr)
        print("Instale un toolchain rv32 y vuelva a intentarlo, o indique el "
              "prefijo con RISCV_PREFIX. Prefijos buscados:", file=sys.stderr)
        for candidato in PREFIJOS_CANDIDATOS:
            print(f"  {candidato}as / {candidato}objdump", file=sys.stderr)
        return 2

    print(f"Toolchain detectado: {prefijo}as / {prefijo}objdump\n")
    try:
        version = subprocess.run([prefijo + "as", "--version"],
                                 capture_output=True, text=True).stdout
        version_toolchain = version.splitlines()[0].strip() if version else ""
    except Exception:
        version_toolchain = ""

    casos = leer_casos(ruta_casos)
    if not casos:
        print("El archivo no contiene casos.", file=sys.stderr)
        return 2

    with tempfile.TemporaryDirectory() as directorio:
        referencias, desensamblados = ensamblar(prefijo, casos, directorio)

    if len(referencias) != len(casos):
        print(f"Aviso: se ensamblaron {len(referencias)} instrucciones pero el "
              f"archivo declara {len(casos)} casos. Revise casos_prueba.txt.",
              file=sys.stderr)
        return 1

    filas = []
    ancho = max(len(instruccion) for instruccion, _ in casos)
    for (instruccion, escenario), referencia, desensamblado in zip(
            casos, referencias, desensamblados):
        modelo, error = ejecutar_herramienta(instruccion)
        coincide = (modelo is not None and modelo == referencia)
        filas.append({
            "instruccion": instruccion,
            "escenario": escenario,
            "modelo": modelo if modelo else f"ERROR: {error}",
            "referencia": referencia,
            "desensamblado": desensamblado,
            "coincide": coincide,
        })
        estado = "OK" if coincide else "FALLA"
        print(f"  {instruccion.ljust(ancho)}  modelo {filas[-1]['modelo']}  "
              f"objdump {referencia}  {estado}")

    aciertos = sum(1 for fila in filas if fila["coincide"])
    print(f"\nResultado: {aciertos}/{len(filas)} casos coinciden.")

    escribir_evidencia(prefijo, filas, version_toolchain)
    print(f"Evidencia escrita en {os.path.relpath(EVIDENCIA, RAIZ)}")

    return 0 if aciertos == len(filas) else 1


if __name__ == "__main__":
    sys.exit(main())
