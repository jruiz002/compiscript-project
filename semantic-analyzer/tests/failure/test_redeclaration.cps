// test_redeclaration.cps
// EXPECTED ERROR: Redeclaration of identifier in same scope
let x: integer = 10;
let x: string = "hello";   // ERROR: redeclaration of x

function foo(): integer {
  return 1;
}

function foo(): string {   // ERROR: duplicate function
  return "hello";
}
