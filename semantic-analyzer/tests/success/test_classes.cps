// test_classes.cps — Classes, inheritance, this, new
class Animal {
  let nombre: string;

  function constructor(nombre: string) {
    this.nombre = nombre;
  }

  function hablar(): string {
    return this.nombre + " hace ruido.";
  }
}

class Perro : Animal {
  function hablar(): string {
    return this.nombre + " ladra.";
  }
}

class Gato : Animal {
  function hablar(): string {
    return this.nombre + " maulla.";
  }
}

let p: Perro = new Perro("Toby");
let g: Gato = new Gato("Michi");

print(p.hablar());
print(g.hablar());
