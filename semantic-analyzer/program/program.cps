// program.cps
// Este archivo demuestra las características del lenguaje Compiscript
// Analizador Semántico: Tipos, Ámbitos, Clases, y Funciones.

// 1. VARIABLES, TIPOS Y CONSTANTES
const PI: integer = 314;
let nombre: string = "Compiscript Demo";
let version: integer = 1;
let activo: boolean = true;

print(nombre);

// 2. ARREGLOS (Matrices y Listas)
let notas: integer[] = [90, 85, 100];
let matriz: integer[][] = [[1, 2], [3, 4]];

print("Notas de estudiantes:");
foreach (nota in notas) {
    if (nota == 100) {
        print("¡Nota perfecta!");
    }
}

// 3. FUNCIONES Y RECURSIÓN
function factorial(n: integer): integer {
    if (n <= 1) { return 1; }
    return n * factorial(n - 1);
}

let calc: integer = factorial(5);
print(calc);

// 4. CLOSURES (Funciones anidadas)
function crearContador(): integer {
    let cuenta: integer = 0;
    function incrementar(): integer {
        cuenta = cuenta + 1;
        return cuenta;
    }
    return incrementar();
}

// 5. CLASES, OBJETOS Y HERENCIA
class Figura {
    let nombre: string;

    function constructor(nombre: string) {
        this.nombre = nombre;
    }

    function obtenerArea(): integer {
        return 0;
    }
}

class Circulo : Figura {
    let radio: integer;

    function constructor(radio: integer) {
        // En Compiscript heredamos la propiedad nombre de Figura
        this.nombre = "Circulo"; 
        this.radio = radio;
    }

    function obtenerArea(): integer {
        return PI * this.radio * this.radio;
    }
}

// Instanciación
let miCirculo: Circulo = new Circulo(5);
let area: integer = miCirculo.obtenerArea();
print(area);

// 6. CONTROL DE FLUJO Y MANEJO DE ERRORES
try {
    let x: integer = 0;
    while (x < 3) {
        x = x + 1;
    }
    
    // Switch case soportado
    switch (x) {
        case 1:
            print("Uno");
        case 3:
            print("Tres");
        default:
            print("Otro");
    }
} catch (error) {
    print("Ocurrió un error");
}
