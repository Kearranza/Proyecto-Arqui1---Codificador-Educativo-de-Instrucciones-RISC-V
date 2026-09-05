#!/usr/bin/env python3
"""
Codificador Educativo de Instrucciones RISC-V.
CE-4301 Arquitectura de Computadores I - Proyecto Individual - 2026-II

Autor: Kevin Carranza Blanco (carnet 2020163275)
Instituto Tecnológico de Costa Rica

Punto de entrada de la herramienta. Conserva el contrato de invocación y de
salida del esqueleto entregado con el kit: un único argumento con la
instrucción, y una línea "HEX: 0x........" en la salida estándar.

La lógica está repartida en el paquete rv32i/ (ver README.md, sección
"Arquitectura del código"). Este archivo es solo la fachada.
"""
import os
import sys

# Permite invocar el script desde cualquier directorio de trabajo.
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from rv32i.encoder import codificar_parseada          # noqa: E402
from rv32i.explain import explicar                    # noqa: E402
from rv32i.isa import SOPORTADAS                      # noqa: E402
from rv32i.parser import ErrorInstruccion, parsear    # noqa: E402


def encode_instruction(instruction: str) -> int:
    """
    Recibe una instrucción como texto, p. ej. "add x5, x6, x7", y retorna
    su codificación de 32 bits como entero (0 <= valor < 2**32).
    """
    parseada = parsear(instruction)
    palabra, _campos = codificar_parseada(parseada)
    return palabra


def explain_instruction(instruction: str, word: int) -> str:
    """
    Retorna el texto que muestra los 32 bits de 'word' divididos en los
    campos del formato correspondiente (R, I, S o B) - con el rango de bits
    y el valor de cada campo - junto con la explicación de cada uno.
    """
    parseada = parsear(instruction)
    _palabra, campos = codificar_parseada(parseada)
    return explicar(parseada, word, campos)


def main():
    if len(sys.argv) != 2:
        print(f'Uso: {sys.argv[0]} "<instruccion>"', file=sys.stderr)
        print(f'Ejemplo: {sys.argv[0]} "add x5, x6, x7"', file=sys.stderr)
        print(f'Instrucciones soportadas: {", ".join(SOPORTADAS)}',
              file=sys.stderr)
        sys.exit(2)

    instruction = sys.argv[1]

    try:
        word = encode_instruction(instruction) & 0xFFFFFFFF
        salida = explain_instruction(instruction, word)
    except ErrorInstruccion as error:
        # Se informa por stderr y se termina con código distinto de cero,
        # sin emitir la línea HEX: una entrada inválida no tiene
        # codificación y no debe producir un resultado que parezca válido.
        print(f"Error: {error}", file=sys.stderr)
        sys.exit(1)

    try:
        print(salida)

        # No modificar el formato de la siguiente línea: la especificación
        # la requiere, literal, para permitir la validación automática.
        print(f"HEX: 0x{word:08x}")
        sys.stdout.flush()
    except BrokenPipeError:
        # Ocurre si la salida se trunca (p. ej. './run.sh "..." | head').
        # No es un error de codificación, así que se termina en silencio.
        os.dup2(os.open(os.devnull, os.O_WRONLY), sys.stdout.fileno())
        sys.exit(0)


if __name__ == "__main__":
    main()
