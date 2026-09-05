# Evidencia de validación contra el toolchain oficial

Proyecto Individual - Codificador Educativo de Instrucciones RISC-V
CE-4301 Arquitectura de Computadores I

Kevin Carranza Blanco - carnet 2020163275
Instituto Tecnológico de Costa Rica

## Entorno de validación

- Prefijo del toolchain: `riscv64-linux-gnu-`
- Ensamblador: `riscv64-linux-gnu-as -march=rv32i -mabi=ilp32`
- Desensamblador: `riscv64-linux-gnu-objdump -d -M numeric,no-aliases`
- Versión reportada: `GNU assembler (GNU Binutils for Ubuntu) 2.46`

Los saltos condicionales se ensamblan como `.+N` / `.-N` porque en sintaxis GNU el tercer operando de `beq`/`bne` es una dirección, no un desplazamiento; `.` denota la dirección de la propia instrucción, de modo que el desplazamiento resultante es exactamente el que codifica la herramienta.

## Resultado global

**36/36 casos coinciden.**

## Tabla comparativa

| # | Instrucción | Escenario | Modelo propio | objdump | Desensamblado | Coincide |
|---|---|---|---|---|---|---|
| 1 | `add x5, x6, x7` | positivo: registros bajos, caso base | `0x007302b3` | `0x007302b3` | `add x5,x6,x7` | Sí |
| 2 | `add x10, x0, x20` | limite: rs1 = x0, la suma copia x20 en x10 | `0x01400533` | `0x01400533` | `add x10,x0,x20` | Sí |
| 3 | `add x31, x31, x31` | limite: los tres campos de registro en su valor maximo | `0x01ff8fb3` | `0x01ff8fb3` | `add x31,x31,x31` | Sí |
| 4 | `sub x8, x9, x10` | positivo: registros bajos, caso base | `0x40a48433` | `0x40a48433` | `sub x8,x9,x10` | Sí |
| 5 | `sub x5, x0, x7` | negativo: x0 - x7 produce la negacion de x7 | `0x407002b3` | `0x407002b3` | `sub x5,x0,x7` | Sí |
| 6 | `sub x31, x30, x29` | limite: registros altos, funct7 = 0100000 | `0x41df0fb3` | `0x41df0fb3` | `sub x31,x30,x29` | Sí |
| 7 | `and x12, x13, x14` | positivo: registros bajos, caso base | `0x00e6f633` | `0x00e6f633` | `and x12,x13,x14` | Sí |
| 8 | `and x0, x1, x2` | limite: rd = x0, el resultado se descarta | `0x0020f033` | `0x0020f033` | `and x0,x1,x2` | Sí |
| 9 | `and x31, x0, x31` | limite: rd y rs2 maximos, rs1 = x0 | `0x01f07fb3` | `0x01f07fb3` | `and x31,x0,x31` | Sí |
| 10 | `or x15, x16, x17` | positivo: registros bajos, caso base | `0x011867b3` | `0x011867b3` | `or x15,x16,x17` | Sí |
| 11 | `or x6, x0, x0` | limite: ambas fuentes son x0, resultado siempre cero | `0x00006333` | `0x00006333` | `or x6,x0,x0` | Sí |
| 12 | `or x31, x1, x31` | limite: rd y rs2 en su valor maximo | `0x01f0efb3` | `0x01f0efb3` | `or x31,x1,x31` | Sí |
| 13 | `addi x5, x6, 100` | positivo: inmediato pequeño positivo | `0x06430293` | `0x06430293` | `addi x5,x6,100` | Sí |
| 14 | `addi x7, x8, -100` | negativo: exige complemento a dos en imm[11:0] | `0xf9c40393` | `0xf9c40393` | `addi x7,x8,-100` | Sí |
| 15 | `addi x9, x10, 2047` | limite: maximo inmediato positivo de 12 bits con signo | `0x7ff50493` | `0x7ff50493` | `addi x9,x10,2047` | Sí |
| 16 | `andi x11, x12, 255` | positivo: mascara de byte | `0x0ff67593` | `0x0ff67593` | `andi x11,x12,255` | Sí |
| 17 | `andi x13, x14, -256` | negativo: mascara con extension de signo | `0xf0077693` | `0xf0077693` | `andi x13,x14,-256` | Sí |
| 18 | `andi x15, x16, -2048` | limite: minimo inmediato de 12 bits con signo | `0x80087793` | `0x80087793` | `andi x15,x16,-2048` | Sí |
| 19 | `lw x1, 4(x2)` | positivo: desplazamiento pequeño respecto a la base | `0x00412083` | `0x00412083` | `lw x1,4(x2)` | Sí |
| 20 | `lw x3, -8(x4)` | negativo: desplazamiento hacia atras | `0xff822183` | `0xff822183` | `lw x3,-8(x4) # fffffff8 <.text+0xfffffff8>` | Sí |
| 21 | `lw x5, 2047(x6)` | limite: maximo desplazamiento positivo | `0x7ff32283` | `0x7ff32283` | `lw x5,2047(x6)` | Sí |
| 22 | `lb x7, 16(x8)` | positivo: desplazamiento pequeño respecto a la base | `0x01040383` | `0x01040383` | `lb x7,16(x8)` | Sí |
| 23 | `lb x9, -1(x10)` | negativo: desplazamiento -1, todos los bits del imm en 1 | `0xfff50483` | `0xfff50483` | `lb x9,-1(x10)` | Sí |
| 24 | `lb x11, -2048(x12)` | limite: minimo desplazamiento representable | `0x80060583` | `0x80060583` | `lb x11,-2048(x12)` | Sí |
| 25 | `sw x1, 12(x2)` | positivo: desplazamiento pequeño, parte imm en dos campos | `0x00112623` | `0x00112623` | `sw x1,12(x2)` | Sí |
| 26 | `sw x3, -16(x4)` | negativo: complemento a dos repartido en imm[11:5] e imm[4:0] | `0xfe322823` | `0xfe322823` | `sw x3,-16(x4) # fffffff0 <.text+0xfffffff0>` | Sí |
| 27 | `sw x5, 2047(x6)` | limite: maximo desplazamiento positivo | `0x7e532fa3` | `0x7e532fa3` | `sw x5,2047(x6)` | Sí |
| 28 | `sb x7, 3(x8)` | positivo: desplazamiento impar, valido en accesos de byte | `0x007401a3` | `0x007401a3` | `sb x7,3(x8)` | Sí |
| 29 | `sb x9, -7(x10)` | negativo: desplazamiento negativo impar | `0xfe950ca3` | `0xfe950ca3` | `sb x9,-7(x10)` | Sí |
| 30 | `sb x11, -2048(x12)` | limite: minimo desplazamiento representable | `0x80b60023` | `0x80b60023` | `sb x11,-2048(x12)` | Sí |
| 31 | `beq x1, x2, 16` | positivo: salto hacia adelante | `0x00208863` | `0x00208863` | `beq x1,x2,88 <.text+0x88>` | Sí |
| 32 | `beq x3, x4, -16` | negativo: salto hacia atras, imm[12] = 1 | `0xfe4188e3` | `0xfe4188e3` | `beq x3,x4,6c <.text+0x6c>` | Sí |
| 33 | `beq x5, x6, 0` | limite: desplazamiento cero, todos los bits del imm en 0 | `0x00628063` | `0x00628063` | `beq x5,x6,80 <.text+0x80>` | Sí |
| 34 | `bne x7, x8, 32` | positivo: salto hacia adelante | `0x02839063` | `0x02839063` | `bne x7,x8,a4 <.text+0xa4>` | Sí |
| 35 | `bne x9, x10, -32` | negativo: salto hacia atras, imm[12] = 1 | `0xfea490e3` | `0xfea490e3` | `bne x9,x10,68 <.text+0x68>` | Sí |
| 36 | `bne x11, x12, 4094` | limite: maximo desplazamiento positivo del formato B | `0x7ec59fe3` | `0x7ec59fe3` | `bne x11,x12,108a <.text+0x108a>` | Sí |

Todos los casos de prueba producen la misma codificación que el toolchain oficial.
