"""
Ensamblado de la palabra de 32 bits a partir de la instrucción parseada.

Cada formato se codifica en una función independiente que devuelve, además
de la palabra, la lista ordenada de campos con su rango de bits. Esa lista
es la única fuente de verdad para el desglose visual: el explicador no
vuelve a calcular posiciones, solo las presenta. Así es imposible que la
codificación y la explicación se contradigan.
"""
from .isa import FORMATO_R, FORMATO_I, FORMATO_S, FORMATO_B
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


def _a_complemento_dos(valor, bits):
    """Representación en complemento a dos de 'valor' en 'bits' bits."""
    return valor & ((1 << bits) - 1)


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


def _codificar_i(p):
    d = p.definicion
    imm12 = _a_complemento_dos(p.imm, 12)
    es_carga = d.mnemonico in ("lw", "lb")

    if es_carga:
        explicacion_imm = (
            f"Desplazamiento de 12 bits con signo: {p.imm}. La dirección "
            f"efectiva de memoria es x{p.rs1} + ({p.imm}). Se extiende con "
            f"signo a 32 bits antes de sumarse.")
        explicacion_rs1 = f"Registro base de la dirección: x{p.rs1}."
        explicacion_rd = f"Registro destino: x{p.rd}. Recibe el dato leído de memoria."
    else:
        explicacion_imm = (
            f"Operando inmediato de 12 bits con signo: {p.imm}. Se extiende "
            f"con signo a 32 bits antes de operar con x{p.rs1}.")
        explicacion_rs1 = f"Registro fuente: x{p.rs1}."
        explicacion_rd = f"Registro destino: x{p.rd}. Aquí se escribe el resultado."

    if p.rd == 0:
        explicacion_rd += " Como es x0, el resultado se descarta."

    campos = [
        Campo("imm[11:0]", 31, 20, imm12, explicacion_imm),
        Campo("rs1", 19, 15, p.rs1, explicacion_rs1),
        Campo("funct3", 14, 12, d.funct3,
              f"Selector de operación dentro del opcode "
              f"{format(d.opcode, '07b')}: identifica '{d.mnemonico}'."),
        Campo("rd", 11, 7, p.rd, explicacion_rd),
        Campo("opcode", 6, 0, d.opcode,
              ("Identifica la familia de cargas desde memoria (LOAD) y, con "
               "ello, el formato I.") if es_carga else
              ("Identifica la familia de operaciones aritmético-lógicas con "
               "inmediato (OP-IMM) y, con ello, el formato I.")),
    ]
    return _ensamblar(campos), campos


def _codificar_s(p):
    d = p.definicion
    imm12 = _a_complemento_dos(p.imm, 12)
    imm_alto = (imm12 >> 5) & 0x7F   # imm[11:5]
    imm_bajo = imm12 & 0x1F          # imm[4:0]

    campos = [
        Campo("imm[11:5]", 31, 25, imm_alto,
              f"Siete bits altos del desplazamiento. El inmediato completo es "
              f"{p.imm}; se parte en dos trozos porque el formato S necesita "
              f"dejar los bits 19:15 y 24:20 libres para rs1 y rs2, que están "
              f"en la misma posición que en el formato R."),
        Campo("rs2", 24, 20, p.rs2,
              f"Registro cuyo contenido se escribe en memoria: x{p.rs2}."),
        Campo("rs1", 19, 15, p.rs1,
              f"Registro base de la dirección: x{p.rs1}."),
        Campo("funct3", 14, 12, d.funct3,
              f"Selector de operación dentro del opcode 0100011: determina el "
              f"ancho del acceso ('{d.mnemonico}')."),
        Campo("imm[4:0]", 11, 7, imm_bajo,
              f"Cinco bits bajos del desplazamiento. Reunidos con imm[11:5] "
              f"forman el valor de 12 bits con signo {p.imm}; la dirección "
              f"efectiva es x{p.rs1} + ({p.imm})."),
        Campo("opcode", 6, 0, d.opcode,
              "Identifica la familia de almacenamientos en memoria (STORE) y, "
              "con ello, el formato S."),
    ]
    return _ensamblar(campos), campos


def _codificar_b(p):
    d = p.definicion
    imm13 = _a_complemento_dos(p.imm, 13)

    bit12 = (imm13 >> 12) & 0x1
    bits10_5 = (imm13 >> 5) & 0x3F
    bits4_1 = (imm13 >> 1) & 0xF
    bit11 = (imm13 >> 11) & 0x1

    alto = (bit12 << 6) | bits10_5     # bits 31:25
    bajo = (bits4_1 << 1) | bit11      # bits 11:7

    campos = [
        Campo("imm[12|10:5]", 31, 25, alto,
              f"Bit de signo del desplazamiento (imm[12] = {bit12}) seguido de "
              f"imm[10:5] = {format(bits10_5, '06b')}. El desplazamiento "
              f"completo es {p.imm} bytes respecto al PC de esta instrucción."),
        Campo("rs2", 24, 20, p.rs2,
              f"Segundo registro a comparar: x{p.rs2}."),
        Campo("rs1", 19, 15, p.rs1,
              f"Primer registro a comparar: x{p.rs1}."),
        Campo("funct3", 14, 12, d.funct3,
              f"Selector de la condición de salto dentro del opcode 1100011: "
              f"identifica '{d.mnemonico}' ({d.descripcion})."),
        Campo("imm[4:1|11]", 11, 7, bajo,
              f"imm[4:1] = {format(bits4_1, '04b')} seguido de imm[11] = "
              f"{bit11}. El bit 0 del desplazamiento no se codifica: siempre "
              f"vale 0 porque las instrucciones están alineadas a 2 bytes, lo "
              f"que duplica el alcance del salto a ±4 KiB."),
        Campo("opcode", 6, 0, d.opcode,
              "Identifica la familia de saltos condicionales (BRANCH) y, con "
              "ello, el formato B."),
    ]
    return _ensamblar(campos), campos


_DESPACHO = {
    FORMATO_R: _codificar_r,
    FORMATO_I: _codificar_i,
    FORMATO_S: _codificar_s,
    FORMATO_B: _codificar_b,
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
