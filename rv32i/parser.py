"""
Parseo de una instrucción en texto ensamblador a una estructura intermedia.

El parser es deliberadamente tolerante en la forma (espacios, comas
opcionales, mayúsculas, comentarios) y estricto en el fondo (mnemónico
soportado, número de operandos, registros válidos, inmediato en rango).
Así la herramienta generaliza a cualquier instrucción del subconjunto sin
aceptar entradas que no tengan una codificación bien definida.
"""
import re

from .isa import (
    TABLA_ISA, NOMBRES_ABI, SOPORTADAS,
    SINTAXIS_R, SINTAXIS_I_ARIT, SINTAXIS_I_LOAD, SINTAXIS_S, SINTAXIS_B,
)


class ErrorInstruccion(ValueError):
    """Error de sintaxis o de rango en la instrucción de entrada."""


class InstruccionParseada:
    """Resultado del parseo: la definición de la ISA más los operandos."""

    __slots__ = ("definicion", "rd", "rs1", "rs2", "imm", "texto")

    def __init__(self, definicion, texto, rd=None, rs1=None, rs2=None, imm=None):
        self.definicion = definicion
        self.texto = texto
        self.rd = rd
        self.rs1 = rs1
        self.rs2 = rs2
        self.imm = imm


# Formas de operando aceptadas.
_RE_OFFSET = re.compile(r"^\s*(?P<imm>[^()\s]+)\s*\(\s*(?P<reg>[^()\s]+)\s*\)\s*$")
_RE_REGISTRO_X = re.compile(r"^x(\d+)$")


def _limpiar(texto):
    """Elimina comentarios (# o //) y normaliza los espacios en blanco."""
    if not isinstance(texto, str):
        raise ErrorInstruccion("la instrucción debe ser una cadena de texto")
    sin_comentario = re.split(r"#|//", texto, maxsplit=1)[0]
    return sin_comentario.strip()


def _partir_operandos(resto):
    """
    Separa los operandos. Las comas son el separador natural, pero también
    se acepta separación solo por espacios ("add x5 x6 x7").
    """
    if not resto:
        return []
    if "," in resto:
        partes = [p.strip() for p in resto.split(",")]
    else:
        partes = resto.split()
    return [p for p in partes if p != ""]


def parsear_registro(token):
    """Convierte 'x13', 'X13' o un nombre ABI ('sp', 't0') en su número."""
    original = token
    token = token.strip().lower()
    if token == "":
        raise ErrorInstruccion("se esperaba un registro y no se encontró ninguno")

    coincidencia = _RE_REGISTRO_X.match(token)
    if coincidencia:
        numero = int(coincidencia.group(1))
        if not 0 <= numero <= 31:
            raise ErrorInstruccion(
                f"registro fuera de rango: '{original}' (RV32I define x0..x31)")
        return numero

    if token in NOMBRES_ABI:
        return NOMBRES_ABI[token]

    raise ErrorInstruccion(
        f"registro no reconocido: '{original}' "
        "(use la forma xN con N entre 0 y 31, o un nombre ABI como sp o t0)")


def parsear_inmediato(token):
    """
    Convierte el inmediato a entero. Acepta decimal con signo, hexadecimal
    (0x), binario (0b) y octal (0o).
    """
    original = token
    token = token.strip().lower().replace("_", "")
    if token == "":
        raise ErrorInstruccion("se esperaba un inmediato y no se encontró ninguno")

    signo = 1
    if token[0] in "+-":
        if token[0] == "-":
            signo = -1
        token = token[1:]

    try:
        if token.startswith("0x"):
            valor = int(token, 16)
        elif token.startswith("0b"):
            valor = int(token, 2)
        elif token.startswith("0o"):
            valor = int(token, 8)
        else:
            valor = int(token, 10)
    except ValueError:
        raise ErrorInstruccion(
            f"inmediato no numérico: '{original}'. Esta herramienta codifica "
            "instrucciones con operandos ya resueltos, por lo que no admite "
            "etiquetas (labels).")

    return signo * valor


def _verificar_rango(definicion, valor):
    """Valida el inmediato contra el rango que permite el formato."""
    from .isa import (FORMATO_I, FORMATO_S, FORMATO_B,
                      IMM_I_MIN, IMM_I_MAX, IMM_S_MIN, IMM_S_MAX,
                      IMM_B_MIN, IMM_B_MAX)

    if definicion.formato == FORMATO_I:
        minimo, maximo, bits = IMM_I_MIN, IMM_I_MAX, 12
    elif definicion.formato == FORMATO_S:
        minimo, maximo, bits = IMM_S_MIN, IMM_S_MAX, 12
    elif definicion.formato == FORMATO_B:
        minimo, maximo, bits = IMM_B_MIN, IMM_B_MAX, 13
        if valor % 2 != 0:
            raise ErrorInstruccion(
                f"el desplazamiento de '{definicion.mnemonico}' debe ser par: "
                f"{valor} no lo es. En formato B el bit 0 es implícitamente 0, "
                "por lo que solo se pueden codificar desplazamientos pares.")
    else:
        return

    if not minimo <= valor <= maximo:
        raise ErrorInstruccion(
            f"inmediato fuera de rango para '{definicion.mnemonico}': {valor}. "
            f"El formato {definicion.formato} codifica un valor con signo de "
            f"{bits} bits, es decir el intervalo [{minimo}, {maximo}].")


def _parsear_offset(token):
    """Parsea la forma 'imm(rs1)' propia de cargas y almacenamientos."""
    coincidencia = _RE_OFFSET.match(token)
    if not coincidencia:
        raise ErrorInstruccion(
            f"se esperaba la forma 'desplazamiento(registro)', p. ej. '8(x6)', "
            f"pero se encontró '{token.strip()}'")
    imm = parsear_inmediato(coincidencia.group("imm"))
    rs1 = parsear_registro(coincidencia.group("reg"))
    return imm, rs1


def _exigir_cantidad(mnemonico, operandos, esperados, ejemplo):
    if len(operandos) != esperados:
        raise ErrorInstruccion(
            f"'{mnemonico}' espera {esperados} operandos y recibió "
            f"{len(operandos)}. Forma correcta: {ejemplo}")


def parsear(texto):
    """
    Parsea una instrucción completa y devuelve una InstruccionParseada.
    Lanza ErrorInstruccion con un mensaje explicativo si la entrada no es
    una instrucción válida del subconjunto soportado.
    """
    limpio = _limpiar(texto)
    if limpio == "":
        raise ErrorInstruccion("no se recibió ninguna instrucción")

    partes = limpio.split(None, 1)
    mnemonico = partes[0].lower().rstrip(",")
    resto = partes[1] if len(partes) > 1 else ""

    definicion = TABLA_ISA.get(mnemonico)
    if definicion is None:
        raise ErrorInstruccion(
            f"instrucción no soportada: '{partes[0]}'. El subconjunto "
            f"soportado es: {', '.join(SOPORTADAS)}.")

    operandos = _partir_operandos(resto)
    sintaxis = definicion.sintaxis

    if sintaxis == SINTAXIS_R:
        _exigir_cantidad(mnemonico, operandos, 3, f"{mnemonico} rd, rs1, rs2")
        rd = parsear_registro(operandos[0])
        rs1 = parsear_registro(operandos[1])
        rs2 = parsear_registro(operandos[2])
        return InstruccionParseada(definicion, limpio, rd=rd, rs1=rs1, rs2=rs2)

    if sintaxis == SINTAXIS_I_ARIT:
        _exigir_cantidad(mnemonico, operandos, 3, f"{mnemonico} rd, rs1, inmediato")
        rd = parsear_registro(operandos[0])
        rs1 = parsear_registro(operandos[1])
        imm = parsear_inmediato(operandos[2])
        _verificar_rango(definicion, imm)
        return InstruccionParseada(definicion, limpio, rd=rd, rs1=rs1, imm=imm)

    if sintaxis == SINTAXIS_I_LOAD:
        _exigir_cantidad(mnemonico, operandos, 2,
                         f"{mnemonico} rd, desplazamiento(rs1)")
        rd = parsear_registro(operandos[0])
        imm, rs1 = _parsear_offset(operandos[1])
        _verificar_rango(definicion, imm)
        return InstruccionParseada(definicion, limpio, rd=rd, rs1=rs1, imm=imm)

    if sintaxis == SINTAXIS_S:
        _exigir_cantidad(mnemonico, operandos, 2,
                         f"{mnemonico} rs2, desplazamiento(rs1)")
        rs2 = parsear_registro(operandos[0])
        imm, rs1 = _parsear_offset(operandos[1])
        _verificar_rango(definicion, imm)
        return InstruccionParseada(definicion, limpio, rs1=rs1, rs2=rs2, imm=imm)

    if sintaxis == SINTAXIS_B:
        _exigir_cantidad(mnemonico, operandos, 3,
                         f"{mnemonico} rs1, rs2, desplazamiento")
        rs1 = parsear_registro(operandos[0])
        rs2 = parsear_registro(operandos[1])
        imm = parsear_inmediato(operandos[2])
        _verificar_rango(definicion, imm)
        return InstruccionParseada(definicion, limpio, rs1=rs1, rs2=rs2, imm=imm)

    raise ErrorInstruccion(f"sintaxis interna desconocida: {sintaxis}")
