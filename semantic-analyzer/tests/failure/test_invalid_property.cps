// test_invalid_property.cps
// EXPECTED ERROR: Property does not exist on type
class Persona {
  let nombre: string;

  function constructor(nombre: string) {
    this.nombre = nombre;
  }
}

let p: Persona = new Persona("Ana");
print(p.edad);      // ERROR: 'edad' does not exist on Persona
print(p.hablar());  // ERROR: 'hablar' is not a method on Persona
