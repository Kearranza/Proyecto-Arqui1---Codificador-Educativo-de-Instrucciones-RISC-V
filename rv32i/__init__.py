"""
Paquete del Codificador Educativo de Instrucciones RISC-V (RV32I).

Módulos:
    isa      Tablas de opcode/funct3/funct7 y metadatos de cada instrucción.
    parser   Texto ensamblador -> estructura intermedia validada.
    encoder  Estructura intermedia -> palabra de 32 bits + lista de campos.
    explain  Palabra + campos -> desglose visual y explicación textual.
"""
from .isa import SOPORTADAS, TABLA_ISA
from .parser import ErrorInstruccion, parsear
from .encoder import codificar, codificar_parseada, Campo
from .explain import explicar

__all__ = [
    "SOPORTADAS", "TABLA_ISA", "ErrorInstruccion", "parsear",
    "codificar", "codificar_parseada", "Campo", "explicar",
]
