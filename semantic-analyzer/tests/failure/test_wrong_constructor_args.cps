// test_wrong_constructor_args.cps
// EXPECTED ERROR: Wrong argument count or type in constructor call

class Punto {
  let x: integer;
  let y: integer;

  function constructor(x: integer, y: integer) {
    this.x = x;
    this.y = y;
  }
}

class Etiqueta {
  let texto: string;

  function constructor(texto: string) {
    this.texto = texto;
  }
}

// ERROR: muy pocos argumentos (espera 2, recibe 1)
let p1 = new Punto(10);

// ERROR: demasiados argumentos (espera 2, recibe 3)
let p2 = new Punto(1, 2, 3);

// ERROR: tipo incorrecto en arg 1 (espera integer, recibe string)
let p3 = new Punto("hola", 5);

// ERROR: tipo incorrecto en arg 1 (espera string, recibe integer)
let e1 = new Etiqueta(42);
