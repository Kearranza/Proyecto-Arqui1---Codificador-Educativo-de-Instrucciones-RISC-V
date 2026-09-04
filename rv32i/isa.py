"""
Tablas de codificación del subconjunto RV32I soportado.

Fuente de los valores de opcode / funct3 / funct7:
    Andrew Waterman, Krste Asanović (eds.),
    "The RISC-V Instruction Set Manual, Volume I: Unprivileged ISA",
    Document Version 20191213, RISC-V Foundation, diciembre 2019.
    - Capítulo 2 "RV32I Base Integer Instruction Set", sección 2.2
      ("Base Instruction Formats") para la disposición de campos del
      formato R.
    - Sección 2.4 ("Integer Computational Instructions") para add, sub,
      and y or.
    - Capítulo 24 ("RV32/64G Instruction Set Listings"), tabla de opcodes,
      usada como verificación cruzada de los valores anteriores.

Todos los valores se escriben aquí en binario para que puedan contrastarse
directamente contra la tabla del manual.
"""

# --- Opcodes (bits 6:0) -----------------------------------------------------
OPCODE_OP = 0b0110011      # Aritmética registro-registro (formato R)

# --- Formatos ---------------------------------------------------------------
FORMATO_R = "R"

# Sintaxis de operandos que acepta el parser para cada instrucción:
#   "rd_rs1_rs2"  ->  op rd, rs1, rs2          (add x5, x6, x7)
SINTAXIS_R = "rd_rs1_rs2"


class DefInstruccion:
    """Descriptor estático de una instrucción del subconjunto soportado."""

    __slots__ = ("mnemonico", "formato", "opcode", "funct3", "funct7",
                 "sintaxis", "descripcion")

    def __init__(self, mnemonico, formato, opcode, funct3, funct7,
                 sintaxis, descripcion):
        self.mnemonico = mnemonico
        self.formato = formato
        self.opcode = opcode
        self.funct3 = funct3
        self.funct7 = funct7          # None cuando el formato no lo usa
        self.sintaxis = sintaxis
        self.descripcion = descripcion


# --- Tabla maestra ----------------------------------------------------------
# Agregar una instrucción del subconjunto es añadir una fila aquí; el resto
# del programa (parser, codificador y explicador) es genérico por formato.
TABLA_ISA = {
    # Aritmética registro-registro — formato R, opcode 0110011
    "add": DefInstruccion("add", FORMATO_R, OPCODE_OP, 0b000, 0b0000000,
                          SINTAXIS_R, "suma con signo de dos registros"),
    "sub": DefInstruccion("sub", FORMATO_R, OPCODE_OP, 0b000, 0b0100000,
                          SINTAXIS_R, "resta con signo de dos registros"),
    "and": DefInstruccion("and", FORMATO_R, OPCODE_OP, 0b111, 0b0000000,
                          SINTAXIS_R, "AND bit a bit de dos registros"),
    "or":  DefInstruccion("or",  FORMATO_R, OPCODE_OP, 0b110, 0b0000000,
                          SINTAXIS_R, "OR bit a bit de dos registros"),
}

SOPORTADAS = list(TABLA_ISA.keys())

# --- Registros --------------------------------------------------------------
# Nombres ABI aceptados además de la forma xN (manual RISC-V, capítulo 25,
# "RISC-V Assembly Programmer's Handbook"). Aceptarlos no es un requisito de
# la especificación, pero evita fallos de parseo si la verificación
# automática usara esta notación.
NOMBRES_ABI = {
    "zero": 0, "ra": 1, "sp": 2, "gp": 3, "tp": 4,
    "t0": 5, "t1": 6, "t2": 7,
    "s0": 8, "fp": 8, "s1": 9,
    "a0": 10, "a1": 11, "a2": 12, "a3": 13,
    "a4": 14, "a5": 15, "a6": 16, "a7": 17,
    "s2": 18, "s3": 19, "s4": 20, "s5": 21, "s6": 22,
    "s7": 23, "s8": 24, "s9": 25, "s10": 26, "s11": 27,
    "t3": 28, "t4": 29, "t5": 30, "t6": 31,
}

