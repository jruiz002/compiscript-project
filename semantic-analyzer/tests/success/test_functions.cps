// test_functions.cps — Valid function declarations and calls
function suma(a: integer, b: integer): integer {
  return a + b;
}

function saludar(nombre: string): string {
  return "Hola, " + nombre;
}

function sinRetorno(x: integer) {
  print(x);
}

let r: integer = suma(3, 4);
let msg: string = saludar("Mundo");
sinRetorno(42);

print(r);
print(msg);
