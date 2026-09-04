"""
Parseo de una instrucción en texto ensamblador a una estructura intermedia.

El parser es deliberadamente tolerante en la forma (espacios, comas
opcionales, mayúsculas, comentarios) y estricto en el fondo (mnemónico
soportado, número de operandos, registros válidos, inmediato en rango).
Así la herramienta generaliza a cualquier instrucción del subconjunto sin
aceptar entradas que no tengan una codificación bien definida.
"""
import re

from .isa import TABLA_ISA, NOMBRES_ABI, SOPORTADAS, SINTAXIS_R


class ErrorInstruccion(ValueError):
    """Error de sintaxis o de rango en la instrucción de entrada."""


class InstruccionParseada:
    """Resultado del parseo: la definición de la ISA más los operandos."""

    __slots__ = ("definicion", "rd", "rs1", "rs2", "texto")

    def __init__(self, definicion, texto, rd=None, rs1=None, rs2=None):
        self.definicion = definicion
        self.texto = texto
        self.rd = rd
        self.rs1 = rs1
        self.rs2 = rs2


# Forma de registro aceptada.
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

    raise ErrorInstruccion(f"sintaxis interna desconocida: {sintaxis}")
