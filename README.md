# Codificador Educativo de Instrucciones RISC-V (RV32I)

**Proyecto individual - CE-4301 Arquitectura de Computadores I**

Kevin Carranza Blanco · carnet 2020163275 · Escuela de Ingeniería en Computadores, Instituto Tecnológico de Costa Rica · II semestre 2026

Herramienta de línea de comandos que recibe una instrucción RV32I en texto, la codifica a 32 bits y muestra el desglose de cada campo del formato correspondiente (R, I, S o B) junto con la explicación de su rol en esa instrucción concreta.

## 1. Preparación y uso

**Requisitos:** Python 3.8 o superior y `bash`. No hay dependencias externas ,el programa usa únicamente la biblioteca estándar, así que no hay `requirements.txt` ni entorno virtual que preparar.

Si `run.sh` perdió el permiso de ejecución al descomprimir la entrega:

```bash
chmod +x run.sh
```

Punto de entrada único:

```bash
./run.sh "<instruccion>"
```

Ejemplos:

```bash
./run.sh "add x5, x6, x7"
./run.sh "addi x10, x1, -12"
./run.sh "lw x5, 8(x6)"
./run.sh "sw x8, -4(x2)"
./run.sh "beq x1, x2, 8"
```

La salida contiene el desglose explicativo y, en su última línea, la codificación en el formato exacto `HEX: 0xXXXXXXXX`.

Una entrada inválida se reporta por `stderr` con código de salida distinto de cero y **no** emite línea `HEX`: una instrucción que no tiene codificación no debe producir algo que parezca una.

## 2. Instrucciones soportadas

### 2.1 Subconjunto y campos de codificación

| Instrucción | Categoría | Formato | opcode | funct3 | funct7 |
|---|---|---|---|---|---|
| `add` | aritmética registro-registro | R | `0110011` | `000` | `0000000` |
| `sub` | aritmética registro-registro | R | `0110011` | `000` | `0100000` |
| `and` | aritmética registro-registro | R | `0110011` | `111` | `0000000` |
| `or`  | aritmética registro-registro | R | `0110011` | `110` | `0000000` |
| `addi` | aritmética con inmediato | I | `0010011` | `000` | - |
| `andi` | aritmética con inmediato | I | `0010011` | `111` | - |
| `lb` | carga desde memoria | I | `0000011` | `000` | - |
| `lw` | carga desde memoria | I | `0000011` | `010` | - |
| `sb` | almacenamiento en memoria | S | `0100011` | `000` | - |
| `sw` | almacenamiento en memoria | S | `0100011` | `010` | - |
| `beq` | salto condicional | B | `1100011` | `000` | - |
| `bne` | salto condicional | B | `1100011` | `001` | -|

Los registros se codifican como el número de `xN` en 5 bits, en los campos `rd`, `rs1` y `rs2` según el formato.

### 2.2 Fuente consultada

Todos los valores de la tabla anterior se tomaron de:

> Andrew Waterman y Krste Asanović (eds.), *The RISC-V Instruction Set Manual, Volume I: Unprivileged ISA*, Document Version 20191213, RISC-V Foundation, diciembre 2019.

En `rv32i/isa.py` los valores están escritos en binario (`0b0110011`) precisamente para poder contrastarlos línea por línea contra esas tablas del manual.

### 2.3 Sintaxis aceptada

| Formato | Forma | Ejemplo |
|---|---|---|
| R | `op rd, rs1, rs2` | `add x5, x6, x7` |
| I aritmético | `op rd, rs1, imm` | `addi x10, x1, -12` |
| I de carga | `op rd, imm(rs1)` | `lw x5, 8(x6)` |
| S | `op rs2, imm(rs1)` | `sw x8, -4(x2)` |
| B | `op rs1, rs2, imm` | `beq x1, x2, 8` |

El parser es tolerante en la forma y estricto en el fondo. Acepta comas opcionales (`add x5 x6 x7`), mayúsculas, comentarios `#` y `//`, nombres ABI de registro (`sp`, `t0`, `a0`) e inmediatos en decimal, `0x`, `0b` y `0o`. No acepta etiquetas: la especificación limita el alcance a instrucciones con los operandos ya resueltos a números.

Rango del inmediato, validado antes de codificar:

- Formatos I y S: valor con signo de 12 bits, `[-2048, 2047]`.
- Formato B: desplazamiento con signo de 13 bits, `[-4096, 4094]`, y siempre par.

## 3. Arquitectura del código

### 3.1 Estructura de archivos

```
.
├── run.sh                   Punto de entrada fijo; invoca el CLI con el argumento recibido.
├── encoder_skeleton.py      Fachada del CLI: argumentos, manejo de errores, línea HEX.
├── rv32i/
│   ├── isa.py               Tabla de opcode/funct3/funct7, registros ABI y rangos de inmediato.
│   ├── parser.py            Texto ensamblador -> estructura intermedia validada.
│   ├── encoder.py           Estructura intermedia -> palabra de 32 bits + lista de campos.
│   └── explain.py           Palabra + campos -> desglose visual y explicación textual.
├── tools/
│   ├── autocheck.py         Comprueba la herramienta contra los vectores del kit.
│   └── validar_toolchain.py Compara los 36 casos propios contra el toolchain oficial.
├── kit/vectores_ejemplo.txt Vectores de referencia entregados con el kit del proyecto.
├── casos_prueba.txt         36 casos propios (12 instrucciones × 3 escenarios).
├── EVIDENCIA.md             Resultado de la comparación contra objdump.
└── README.md                Este documento.
```

### 3.2 Flujo de ejecución

```
"add x5, x6, x7"
      │
      ▼  parser.parsear()          valida mnemónico, operandos, registros y rango
InstruccionParseada
      │
      ▼  encoder.codificar_parseada()
(palabra de 32 bits, lista de Campo)
      │
      ▼  explain.explicar()
desglose visual + explicación  ->  stdout
HEX: 0x007302b3                ->  stdout
```

### 3.3 Decisiones de diseño

**Los campos son la única fuente de verdad.** El codificador no arma la palabra de 32 bits por un lado y el dibujo por otro. Construye una lista de objetos `Campo` (nombre, rango de bits, valor y explicación) y la palabra se obtiene desplazando y combinando esa misma lista. `explain.py` solo presenta lo que recibe; nunca recalcula una posición de bit. Así es estructuralmente imposible que el desglose visual diga una cosa y la codificación real sea otra.

**Una tabla, no un condicional por instrucción.** `TABLA_ISA` en `isa.py` tiene una fila por instrucción con su formato, opcode, funct3, funct7 y forma sintáctica. El parser, el codificador y el explicador son genéricos por formato (R, I, S, B), no por mnemónico. Agregar una instrucción del mismo formato es agregar una fila, no tocar la lógica; y como la herramienta se evalúa con instrucciones que el estudiante no eligió, generalizar por formato es lo que garantiza que funcione con cualquier combinación de registros e inmediatos del subconjunto.

**Validar antes de codificar.** El rango del inmediato y la paridad del desplazamiento de salto se revisan en el parser, no en el codificador. Un valor fuera de rango produce un mensaje que dice cuál es el intervalo válido y por qué, en lugar de truncarse en silencio y dar una codificación plausible pero equivocada.

### 3.4 El caso delicado: el inmediato del formato B

Es el único formato donde el inmediato no ocupa bits contiguos. El desplazamiento es un valor con signo de 13 bits cuyo bit 0 nunca se almacena, siempre vale 0, porque las instrucciones están alineadas a 2 bytes, y los 12 bits restantes se reparten así:

| Bits de la instrucción | Contenido |
|---|---|
| 31 | `imm[12]` (bit de signo) |
| 30:25 | `imm[10:5]` |
| 11:8 | `imm[4:1]` |
| 7 | `imm[11]` |

El reordenamiento no es arbitrario: mantiene `rs1`, `rs2` y `funct3` en la misma posición que en los demás formatos, de modo que el hardware puede empezar a leer los registros antes de terminar de decodificar la instrucción.

Ejemplo con `beq x1, x2, -80`. En complemento a dos de 13 bits, −80 es `1111110110000`, de donde `imm[12] = 1`, `imm[10:5] = 111101`, `imm[4:1] = 1000` e `imm[11] = 1`. Los campos quedan `imm[12|10:5] = 1111101` en los bits 31:25 e `imm[4:1|11] = 10001` en los bits 11:7, que es exactamente lo que muestra la salida de la sección 4.4.

## 4. Ejemplos de salida explicativa

Un ejemplo por formato, copiado de la salida real de la herramienta.

### 4.1 Formato R - `add x5, x6, x7`

```
==============================================================================
  CODIFICADOR DE INSTRUCCIONES RISC-V (RV32I)
==============================================================================
  Instrucción : add x5, x6, x7
  Mnemónico   : add  (suma con signo de dos registros)
  Formato     : R  (aritmética registro-registro)
  Operación   : x5 <- x6 + x7
------------------------------------------------------------------------------
  Hexadecimal : 0x007302b3
  Binario     : 00000000011100110000001010110011
  Por campos  : 0000000 00111 00110 000 00101 0110011
------------------------------------------------------------------------------

  Desglose de los 32 bits (bit 31 a la izquierda, bit 0 a la derecha):

  +---------+---------+---------+---------+--------+---------+
  | [31:25] | [24:20] | [19:15] | [14:12] | [11:7] |  [6:0]  |
  +---------+---------+---------+---------+--------+---------+
  | 0000000 |  00111  |  00110  |   000   | 00101  | 0110011 |
  |  funct7 |   rs2   |   rs1   |  funct3 |   rd   |  opcode |
  +---------+---------+---------+---------+--------+---------+

------------------------------------------------------------------------------
  Significado de cada campo:

  funct7  ->  bits [31:25]  =  0b0000000  (decimal 0, hex 0x0)
      Selector secundario de operación. Junto con funct3 y el opcode
      distingue 'add' de las demás operaciones registro-registro (p. ej.
      add y sub comparten funct3 y solo difieren en este campo).

  rs2  ->  bits [24:20]  =  0b00111  (decimal 7, hex 0x7)
      Segundo registro fuente: x7.

  rs1  ->  bits [19:15]  =  0b00110  (decimal 6, hex 0x6)
      Primer registro fuente: x6.

  funct3  ->  bits [14:12]  =  0b000  (decimal 0, hex 0x0)
      Selector primario de operación dentro del opcode 0110011.

  rd  ->  bits [11:7]  =  0b00101  (decimal 5, hex 0x5)
      Registro destino: x5. Aquí se escribe el resultado.

  opcode  ->  bits [6:0]  =  0b0110011  (decimal 51, hex 0x33)
      Identifica la familia de operaciones aritmético-lógicas registro-
      registro (OP) y, con ello, el formato R.
==============================================================================
HEX: 0x007302b3
```

### 4.2 Formato I - `addi x10, x1, -12`

```
==============================================================================
  CODIFICADOR DE INSTRUCCIONES RISC-V (RV32I)
==============================================================================
  Instrucción : addi x10, x1, -12
  Mnemónico   : addi  (suma un inmediato de 12 bits con signo a un registro)
  Formato     : I  (operando inmediato de 12 bits)
  Operación   : x10 <- x1 + (-12)
------------------------------------------------------------------------------
  Hexadecimal : 0xff408513
  Binario     : 11111111010000001000010100010011
  Por campos  : 111111110100 00001 000 01010 0010011
------------------------------------------------------------------------------

  Desglose de los 32 bits (bit 31 a la izquierda, bit 0 a la derecha):

  +--------------+---------+---------+--------+---------+
  |   [31:20]    | [19:15] | [14:12] | [11:7] |  [6:0]  |
  +--------------+---------+---------+--------+---------+
  | 111111110100 |  00001  |   000   | 01010  | 0010011 |
  |  imm[11:0]   |   rs1   |  funct3 |   rd   |  opcode |
  +--------------+---------+---------+--------+---------+

------------------------------------------------------------------------------
  Significado de cada campo:

  imm[11:0]  ->  bits [31:20]  =  0b111111110100  (decimal 4084, hex 0xff4)
      Operando inmediato de 12 bits con signo: -12. Se extiende con
      signo a 32 bits antes de operar con x1.

  rs1  ->  bits [19:15]  =  0b00001  (decimal 1, hex 0x1)
      Registro fuente: x1.

  funct3  ->  bits [14:12]  =  0b000  (decimal 0, hex 0x0)
      Selector de operación dentro del opcode 0010011: identifica
      'addi'.

  rd  ->  bits [11:7]  =  0b01010  (decimal 10, hex 0xa)
      Registro destino: x10. Aquí se escribe el resultado.

  opcode  ->  bits [6:0]  =  0b0010011  (decimal 19, hex 0x13)
      Identifica la familia de operaciones aritmético-lógicas con
      inmediato (OP-IMM) y, con ello, el formato I.
==============================================================================
HEX: 0xff408513
```

### 4.3 Formato S - `sw x8, -4(x2)`

```
==============================================================================
  CODIFICADOR DE INSTRUCCIONES RISC-V (RV32I)
==============================================================================
  Instrucción : sw x8, -4(x2)
  Mnemónico   : sw  (almacena en memoria la palabra de 32 bits de un registro)
  Formato     : S  (almacenamiento en memoria)
  Operación   : memoria[x2 + (-4)] <- la palabra de 32 bits de x8
------------------------------------------------------------------------------
  Hexadecimal : 0xfe812e23
  Binario     : 11111110100000010010111000100011
  Por campos  : 1111111 01000 00010 010 11100 0100011
------------------------------------------------------------------------------

  Desglose de los 32 bits (bit 31 a la izquierda, bit 0 a la derecha):

  +-----------+---------+---------+---------+----------+---------+
  |  [31:25]  | [24:20] | [19:15] | [14:12] |  [11:7]  |  [6:0]  |
  +-----------+---------+---------+---------+----------+---------+
  |  1111111  |  01000  |  00010  |   010   |  11100   | 0100011 |
  | imm[11:5] |   rs2   |   rs1   |  funct3 | imm[4:0] |  opcode |
  +-----------+---------+---------+---------+----------+---------+

------------------------------------------------------------------------------
  Significado de cada campo:

  imm[11:5]  ->  bits [31:25]  =  0b1111111  (decimal 127, hex 0x7f)
      Siete bits altos del desplazamiento. El inmediato completo es -4;
      se parte en dos trozos porque el formato S necesita dejar los bits
      19:15 y 24:20 libres para rs1 y rs2, que están en la misma
      posición que en el formato R.

  rs2  ->  bits [24:20]  =  0b01000  (decimal 8, hex 0x8)
      Registro cuyo contenido se escribe en memoria: x8.

  rs1  ->  bits [19:15]  =  0b00010  (decimal 2, hex 0x2)
      Registro base de la dirección: x2.

  funct3  ->  bits [14:12]  =  0b010  (decimal 2, hex 0x2)
      Selector de operación dentro del opcode 0100011: determina el
      ancho del acceso ('sw').

  imm[4:0]  ->  bits [11:7]  =  0b11100  (decimal 28, hex 0x1c)
      Cinco bits bajos del desplazamiento. Reunidos con imm[11:5] forman
      el valor de 12 bits con signo -4; la dirección efectiva es x2 +
      (-4).

  opcode  ->  bits [6:0]  =  0b0100011  (decimal 35, hex 0x23)
      Identifica la familia de almacenamientos en memoria (STORE) y, con
      ello, el formato S.
==============================================================================
HEX: 0xfe812e23
```

### 4.4 Formato B - `beq x1, x2, -80`

```
==============================================================================
  CODIFICADOR DE INSTRUCCIONES RISC-V (RV32I)
==============================================================================
  Instrucción : beq x1, x2, -80
  Mnemónico   : beq  (salta si los dos registros son iguales)
  Formato     : B  (salto condicional)
  Operación   : si x1 == x2 entonces PC <- PC + (-80)
------------------------------------------------------------------------------
  Hexadecimal : 0xfa2088e3
  Binario     : 11111010001000001000100011100011
  Por campos  : 1111101 00010 00001 000 10001 1100011
------------------------------------------------------------------------------

  Desglose de los 32 bits (bit 31 a la izquierda, bit 0 a la derecha):

  +--------------+---------+---------+---------+-------------+---------+
  |   [31:25]    | [24:20] | [19:15] | [14:12] |    [11:7]   |  [6:0]  |
  +--------------+---------+---------+---------+-------------+---------+
  |   1111101    |  00010  |  00001  |   000   |    10001    | 1100011 |
  | imm[12|10:5] |   rs2   |   rs1   |  funct3 | imm[4:1|11] |  opcode |
  +--------------+---------+---------+---------+-------------+---------+

------------------------------------------------------------------------------
  Significado de cada campo:

  imm[12|10:5]  ->  bits [31:25]  =  0b1111101  (decimal 125, hex 0x7d)
      Bit de signo del desplazamiento (imm[12] = 1) seguido de imm[10:5]
      = 111101. El desplazamiento completo es -80 bytes respecto al PC
      de esta instrucción.

  rs2  ->  bits [24:20]  =  0b00010  (decimal 2, hex 0x2)
      Segundo registro a comparar: x2.

  rs1  ->  bits [19:15]  =  0b00001  (decimal 1, hex 0x1)
      Primer registro a comparar: x1.

  funct3  ->  bits [14:12]  =  0b000  (decimal 0, hex 0x0)
      Selector de la condición de salto dentro del opcode 1100011:
      identifica 'beq' (salta si los dos registros son iguales).

  imm[4:1|11]  ->  bits [11:7]  =  0b10001  (decimal 17, hex 0x11)
      imm[4:1] = 1000 seguido de imm[11] = 1. El bit 0 del
      desplazamiento no se codifica: siempre vale 0 porque las
      instrucciones están alineadas a 2 bytes, lo que duplica el alcance
      del salto a ±4 KiB.

  opcode  ->  bits [6:0]  =  0b1100011  (decimal 99, hex 0x63)
      Identifica la familia de saltos condicionales (BRANCH) y, con
      ello, el formato B.
==============================================================================
HEX: 0xfa2088e3
```

## 5. Validación

### 5.1 Toolchain utilizado

Se usó el ensamblador y el `objdump` de GNU binutils para RISC-V, sobre Ubuntu en WSL. Basta con las binutils; no hace falta el compilador completo, porque la validación solo ensambla y desensambla, no compila:

```bash
sudo apt update
sudo apt install binutils-riscv64-linux-gnu
```

Eso instala `riscv64-linux-gnu-as` y `riscv64-linux-gnu-objdump`. Aunque el prefijo diga `riscv64`, el ensamblado se hace con `-march=rv32i -mabi=ilp32`, es decir contra RV32I de 32 bits. Un toolchain con otro prefijo (`riscv32-unknown-elf-`, por ejemplo) funciona igual: el script lo detecta solo, y también se le puede indicar con la variable de entorno `RISCV_PREFIX`.

### 5.2 Comparación contra el toolchain oficial

```bash
python3 tools/validar_toolchain.py
```

El script toma los 36 casos de `casos_prueba.txt`, los ensambla con `as -march=rv32i -mabi=ilp32`, obtiene la codificación de referencia con `objdump -d -M numeric,no-aliases`, la compara contra la salida de `./run.sh` y escribe el resultado en `EVIDENCIA.md`.

**Resultado: 36/36 casos coinciden.** La tabla completa (instrucción, escenario, codificación del modelo propio, codificación de `objdump`, desensamblado y coincidencia) está en [EVIDENCIA.md](EVIDENCIA.md).

Los 36 casos son 3 por cada una de las 12 instrucciones, con un escenario positivo, uno negativo y uno límite según lo que tenga sentido ejercitar en cada formato:

- **Formato R** (sin inmediato): registros bajos, uso de `x0`, y `x31` en los tres campos de registro para ejercitar los 5 bits en su extremo.
- **Formatos I y S**: inmediato positivo, negativo, y en el límite representable (`+2047` o `-2048`).
- **Formato B**: desplazamiento hacia adelante, hacia atrás (con `imm[12] = 1`), y caso límite (desplazamiento cero o el máximo `+4094`).

Un detalle de lectura de la tabla: en la columna del desensamblado los saltos aparecen como `beq x1,x2,88 <.text+0x88>` en lugar del desplazamiento original. Es el comportamiento normal de `objdump`, en sintaxis GNU el tercer operando de un salto es una dirección, no un desplazamiento, y por eso los casos se ensamblan como `.+N` / `.-N`, donde `.` es la dirección de la propia instrucción. El desplazamiento codificado es el mismo, y es lo que se compara.

### 5.3 Verificación rápida contra los vectores del kit

Independiente de lo anterior, y sin necesidad del toolchain:

```bash
python3 tools/autocheck.py
```

Invoca `./run.sh` con cada línea de `kit/vectores_ejemplo.txt` y compara la línea `HEX` contra la codificación de referencia que trae el archivo. **Resultado: 36/36 vectores correctos.** Sirve como comprobación previa e independiente, no como sustituto de la validación contra el toolchain.

## 6. Referencias

1. Andrew Waterman y Krste Asanović (eds.). *The RISC-V Instruction Set Manual, Volume I: Unprivileged ISA*. Document Version 20191213. RISC-V Foundation, diciembre 2019. <https://riscv.org/technical/specifications/>
2. GNU Binutils - `as` y `objdump` para RISC-V. Paquete `binutils-riscv64-linux-gnu` de Ubuntu.
