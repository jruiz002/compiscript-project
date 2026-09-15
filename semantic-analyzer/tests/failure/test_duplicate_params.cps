// test_duplicate_params.cps
// EXPECTED ERROR: Duplicate parameter name in function declaration
function suma(a: integer, a: integer): integer {
  return a + a;               // ERROR: 'a' declarado dos veces como parámetro
}

function saludar(nombre: string, nombre: string): string {
  return "Hola " + nombre;    // ERROR: 'nombre' declarado dos veces
}

class Punto {
  let x: integer;

  function constructor(x: integer, x: integer) {
    this.x = x;               // ERROR: 'x' duplicado en el constructor
  }
}
