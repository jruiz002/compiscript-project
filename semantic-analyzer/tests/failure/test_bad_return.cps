// test_bad_return.cps
// EXPECTED ERROR: Return type mismatches
function getNumber(): integer {
  return "hola";    // ERROR: expected integer, got string
}

function getNothing() {
  return 42;        // ERROR: void function returning value
}

return 1;           // ERROR: return outside function
