// test_const_reassign.cps
// EXPECTED ERROR: Cannot assign to constant
const PI: integer = 314;
PI = 300;    // ERROR: cannot assign to constant

const MSG: string = "hello";
MSG = "world";  // ERROR
