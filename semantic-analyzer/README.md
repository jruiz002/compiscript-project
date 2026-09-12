# Compiscript Compiler — M1: Análisis Semántico

📺 **[Video de explicación](https://www.youtube.com/watch?v=dK3sldFkwLs)** — arquitectura, tabla de símbolos, sistema de tipos, IDE y tests en vivo.

## 🚀 Inicio Rápido

### Opción 1: Setup Local (recomendado para desarrollo)

```bash
# 1. Clonar el repositorio y entrar al directorio
cd compiscript-compiler

# 2. Ejecutar el script de setup (descarga ANTLR, instala deps, genera parser)
chmod +x setup.sh
./setup.sh

# 3. Compilar un archivo de prueba
python3 compiler/driver.py program/program.cps

# 4. Correr la batería de tests
python3 tests/run_tests.py

# 5. Lanzar el IDE web
python3 ide/server.py
# → Abrir http://localhost:5000
```

### Opción 2: Docker (Evaluación)

```bash
# 1. Construir la imagen de Docker
docker build --rm . -t csp-image

# 2. Correr el contenedor mapeando el puerto para el IDE web
docker run --rm -ti -p 8080:5000 -v "$(pwd)/program":/program csp-image
# → El IDE estará disponible en http://localhost:8080

# 3. (Opcional) Para correr el analizador por consola desde adentro de Docker:
# docker run --rm -ti -v "$(pwd)/program":/program csp-image bash
# python3 program/Driver.py program/program.cps
```

---

## 🛠 CLI: `compiler/driver.py`

```
python3 compiler/driver.py <archivo.cps> [opciones]

Opciones:
  --ast          Imprimir el AST como JSON
  --ast-out PATH Renderizar el AST como SVG en la ruta dada
  --symbols      Imprimir la tabla de símbolos como JSON
  --json         Toda la salida como JSON estructurado
```

**Ejemplos:**

```bash
# Análisis semántico básico
python3 compiler/driver.py program/program.cps

# Con tabla de símbolos y AST
python3 compiler/driver.py program/program.cps --symbols --ast

# Renderizar el árbol sintáctico
python3 compiler/driver.py program/program.cps --ast-out output/ast

# Salida JSON para integración con otras herramientas
python3 compiler/driver.py program/program.cps --json
```

**Códigos de salida:**
- `0` → Sin errores semánticos
- `1` → Se encontraron errores

---

## 🧪 Tests

```bash
# Correr todos los tests
python3 tests/run_tests.py

# Modo verboso (muestra detalles de cada error)
python3 tests/run_tests.py --verbose

# Filtrar por nombre
python3 tests/run_tests.py --filter classes

# Salida JSON
python3 tests/run_tests.py --json
```

### Estructura de Tests

| Directorio | Propósito |
|------------|-----------|
| `tests/success/` | Programas válidos — deben compilar sin errores |
| `tests/failure/` | Programas con errores intencionales — deben producir al menos 1 error |

---

## 🌐 IDE Web

```bash
python3 ide/server.py
```

Abre `http://localhost:5000` en el navegador.

**Características del IDE:**
- Editor de código con numeración de líneas y soporte Tab
- Compilación con `Ctrl+Enter` o botón ▶
- Panel de diagnósticos con errores y advertencias por línea
- Tabla de símbolos navegable con árbol de scopes
- Visualización del AST (requiere `graphviz` instalado en el sistema)
- Ejemplos de código predefinidos
- Tema oscuro premium

---

## 📦 Dependencias

| Paquete | Versión | Propósito |
|---------|---------|-----------|
| `antlr4-python3-runtime` | 4.13.2 | Runtime del parser ANTLR4 |
| `flask` | 3.1.1 | Servidor web del IDE |
| `flask-cors` | 5.0.1 | CORS para la API del compilador |
| `graphviz` | 0.20.3 | Renderizado del AST (Python lib) |
| `graphviz` (sistema) | cualquiera | Binario para renderizar SVG |

Para instalar el binario de graphviz:
```bash
# macOS
brew install graphviz

# Ubuntu/Debian
apt-get install graphviz
```
