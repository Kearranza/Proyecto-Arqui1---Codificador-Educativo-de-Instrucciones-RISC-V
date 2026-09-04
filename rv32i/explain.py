"""
Presentación de la instrucción codificada.

Toma la palabra de 32 bits y la lista de campos producida por el
codificador y genera el desglose visual: una tabla que muestra cada campo
con su rango de bits y su valor binario, seguida de la explicación del rol
de cada campo en esa instrucción concreta.
"""
import textwrap

from .isa import FORMATO_R

ANCHO = 78

NOMBRE_FORMATO = {
    FORMATO_R: "R  (aritmética registro-registro)",
}


def _linea(caracter="="):
    return caracter * ANCHO


def _binario_agrupado(campos):
    """Los 32 bits en el orden de la palabra, separados por campo."""
    return " ".join(campo.binario for campo in campos)


def _tabla_campos(campos):
    """
    Construye la tabla ASCII de los campos. Las columnas se dimensionan
    según el contenido, de modo que sirve igual para los cuatro formatos.
    """
    celdas = []
    for campo in campos:
        rango = campo.rango
        binario = campo.binario
        nombre = campo.nombre
        ancho = max(len(rango), len(binario), len(nombre)) + 2
        celdas.append((ancho, rango, binario, nombre))

    borde = "+" + "+".join("-" * ancho for ancho, _, _, _ in celdas) + "+"
    fila_rango = "|" + "|".join(r.center(a) for a, r, _, _ in celdas) + "|"
    fila_bits = "|" + "|".join(b.center(a) for a, _, b, _ in celdas) + "|"
    fila_nombre = "|" + "|".join(n.center(a) for a, _, _, n in celdas) + "|"

    return "\n".join([borde, fila_rango, borde, fila_bits, fila_nombre, borde])


def _detalle_campos(campos):
    partes = []
    for campo in campos:
        decimal = campo.valor
        cabecera = (f"  {campo.nombre}  ->  bits {campo.rango}  =  "
                    f"0b{campo.binario}  (decimal {decimal}, "
                    f"hex 0x{decimal:x})")
        cuerpo = textwrap.fill(
            campo.explicacion,
            width=ANCHO - 6,
            initial_indent="      ",
            subsequent_indent="      ",
        )
        partes.append(cabecera + "\n" + cuerpo)
    return "\n\n".join(partes)


def _resumen_semantico(p):
    """Frase que describe qué hace la instrucción con sus operandos."""
    d = p.definicion
    m = d.mnemonico

    if d.formato == FORMATO_R:
        simbolo = {"add": "+", "sub": "-", "and": "&", "or": "|"}[m]
        return f"x{p.rd} <- x{p.rs1} {simbolo} x{p.rs2}"

    return ""


def explicar(p, palabra, campos):
    """Genera el texto completo de salida para una instrucción codificada."""
    d = p.definicion
    binario_plano = format(palabra, "032b")

    lineas = [
        _linea("="),
        "  CODIFICADOR DE INSTRUCCIONES RISC-V (RV32I)",
        _linea("="),
        f"  Instrucción : {p.texto}",
        f"  Mnemónico   : {d.mnemonico}  ({d.descripcion})",
        f"  Formato     : {NOMBRE_FORMATO[d.formato]}",
        f"  Operación   : {_resumen_semantico(p)}",
        _linea("-"),
        f"  Hexadecimal : 0x{palabra:08x}",
        f"  Binario     : {binario_plano}",
        f"  Por campos  : {_binario_agrupado(campos)}",
        _linea("-"),
        "",
        "  Desglose de los 32 bits (bit 31 a la izquierda, bit 0 a la derecha):",
        "",
    ]

    tabla = _tabla_campos(campos)
    sangria = "  "
    lineas.extend(sangria + fila for fila in tabla.split("\n"))

    lineas.extend([
        "",
        _linea("-"),
        "  Significado de cada campo:",
        "",
        _detalle_campos(campos),
        _linea("="),
    ])

    return "\n".join(lineas)
