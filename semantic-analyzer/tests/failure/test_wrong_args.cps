// test_wrong_args.cps
// EXPECTED ERROR: Wrong argument count or type in function calls
function suma(a: integer, b: integer): integer {
  return a + b;
}

let r1 = suma(1);            // ERROR: too few args
let r2 = suma(1, 2, 3);      // ERROR: too many args
let r3 = suma("hola", 2);    // ERROR: wrong type for arg 1
