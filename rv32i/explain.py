
#Presentación de la instrucción codificada.

import textwrap

from .isa import FORMATO_R, FORMATO_I, FORMATO_S, FORMATO_B

ANCHO = 78

NOMBRE_FORMATO = {
    FORMATO_R: "R  (aritmética registro-registro)",
    FORMATO_I: "I  (operando inmediato de 12 bits)",
    FORMATO_S: "S  (almacenamiento en memoria)",
    FORMATO_B: "B  (salto condicional)",
}


def _linea(caracter="="):
    return caracter * ANCHO


def _binario_agrupado(campos):
    """Los 32 bits en el orden de la palabra, separados por campo."""
    return " ".join(campo.binario for campo in campos)


def _tabla_campos(campos):
    
    #Construye la tabla ASCII de los campos. Las columnas se dimensionan
    #según el contenido, de modo que sirve igual para los cuatro formatos.
    
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


def _operando_inmediato(valor):
    return f"({valor})" if valor < 0 else str(valor)


def _resumen_semantico(p):
    #Frase que describe qué hace la instrucción con sus operandos.
    d = p.definicion
    m = d.mnemonico

    if d.formato == FORMATO_R:
        simbolo = {"add": "+", "sub": "-", "and": "&", "or": "|"}[m]
        return f"x{p.rd} <- x{p.rs1} {simbolo} x{p.rs2}"

    if d.formato == FORMATO_I:
        if m in ("lw", "lb"):
            ancho = "32 bits" if m == "lw" else "8 bits con extensión de signo"
            return (f"x{p.rd} <- memoria[x{p.rs1} + ({p.imm})], leyendo {ancho}")
        simbolo = {"addi": "+", "andi": "&"}[m]
        return f"x{p.rd} <- x{p.rs1} {simbolo} {_operando_inmediato(p.imm)}"

    if d.formato == FORMATO_S:
        ancho = "la palabra de 32 bits" if m == "sw" else "el byte bajo"
        return f"memoria[x{p.rs1} + ({p.imm})] <- {ancho} de x{p.rs2}"

    if d.formato == FORMATO_B:
        condicion = "==" if m == "beq" else "!="
        return (f"si x{p.rs1} {condicion} x{p.rs2} entonces "
                f"PC <- PC + {_operando_inmediato(p.imm)}")

    return ""


def explicar(p, palabra, campos):
    #Genera el texto completo de salida para una instrucción codificada.
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
