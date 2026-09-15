// test_scoping.cps — Block scoping and nested scopes
let x: integer = 10;

{
  let y: integer = 20;
  let z: integer = x + y;   // x is accessible from outer scope
  print(z);
}

// y and z not accessible here, but x still is
print(x);

{
  let x: integer = 99;   // shadows outer x — valid in new scope
  print(x);
}

// outer x is restored
print(x);
