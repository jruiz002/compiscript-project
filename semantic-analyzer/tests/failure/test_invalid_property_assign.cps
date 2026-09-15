// test_invalid_property_assign.cps
// EXPECTED ERROR: property assignment as a *statement* (obj.prop = val;) must be
// validated the same way as the expression form. See H-01.
class Animal {
  let nombre: string;
}

let a: Animal = new Animal();
a.noExiste = 5;    // ERROR: 'noExiste' does not exist on Animal
a.nombre = 123;     // ERROR: integer assigned to string
