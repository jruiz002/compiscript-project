// test_undeclared_variable.cps
// EXPECTED ERROR: Use of undeclared identifier
print(variableNoDeclarada);     // ERROR
let x: integer = y + 1;        // ERROR: y not declared
