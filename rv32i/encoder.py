"""
Ensamblado de la palabra de 32 bits a partir de la instrucción parseada.

Cada formato se codifica en una función independiente que devuelve, además
de la palabra, la lista ordenada de campos con su rango de bits. Esa lista
es la única fuente de verdad para el desglose visual: el explicador no
vuelve a calcular posiciones, solo las presenta. Así es imposible que la
codificación y la explicación se contradigan.
"""
from .isa import FORMATO_R
from .parser import ErrorInstruccion, parsear


class Campo:
    """Un campo de la instrucción: nombre, rango de bits y valor."""

    __slots__ = ("nombre", "bit_hi", "bit_lo", "valor", "explicacion")

    def __init__(self, nombre, bit_hi, bit_lo, valor, explicacion):
        self.nombre = nombre
        self.bit_hi = bit_hi
        self.bit_lo = bit_lo
        self.valor = valor
        self.explicacion = explicacion

    @property
    def ancho(self):
        return self.bit_hi - self.bit_lo + 1

    @property
    def binario(self):
        return format(self.valor, f"0{self.ancho}b")

    @property
    def rango(self):
        if self.bit_hi == self.bit_lo:
            return f"[{self.bit_hi}]"
        return f"[{self.bit_hi}:{self.bit_lo}]"


def _campo(valor, bits):
    """Recorta un valor al ancho de campo indicado."""
    return valor & ((1 << bits) - 1)


def _ensamblar(campos):
    """Combina los campos en la palabra de 32 bits."""
    palabra = 0
    for campo in campos:
        palabra |= _campo(campo.valor, campo.ancho) << campo.bit_lo
    return palabra & 0xFFFFFFFF


def _codificar_r(p):
    d = p.definicion
    campos = [
        Campo("funct7", 31, 25, d.funct7,
              f"Selector secundario de operación. Junto con funct3 y el opcode "
              f"distingue '{d.mnemonico}' de las demás operaciones "
              f"registro-registro (p. ej. add y sub comparten funct3 y solo "
              f"difieren en este campo)."),
        Campo("rs2", 24, 20, p.rs2,
              f"Segundo registro fuente: x{p.rs2}."),
        Campo("rs1", 19, 15, p.rs1,
              f"Primer registro fuente: x{p.rs1}."),
        Campo("funct3", 14, 12, d.funct3,
              f"Selector primario de operación dentro del opcode 0110011."),
        Campo("rd", 11, 7, p.rd,
              f"Registro destino: x{p.rd}. Aquí se escribe el resultado."
              + (" Como es x0, el resultado se descarta: x0 está cableado a cero."
                 if p.rd == 0 else "")),
        Campo("opcode", 6, 0, d.opcode,
              "Identifica la familia de operaciones aritmético-lógicas "
              "registro-registro (OP) y, con ello, el formato R."),
    ]
    return _ensamblar(campos), campos


_DESPACHO = {
    FORMATO_R: _codificar_r,
}


def codificar_parseada(p):
    """Codifica una InstruccionParseada. Devuelve (palabra, campos)."""
    codificador = _DESPACHO.get(p.definicion.formato)
    if codificador is None:
        raise ErrorInstruccion(
            f"formato sin codificador: {p.definicion.formato}")
    return codificador(p)


def codificar(texto):
    """Parsea y codifica una instrucción en texto. Devuelve (palabra, campos, parseada)."""
    p = parsear(texto)
    palabra, campos = codificar_parseada(p)
    return palabra, campos, p
