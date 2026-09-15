// test_type_mismatch_arithmetic.cps
// EXPECTED ERROR: Cannot apply arithmetic to non-numeric types
let a: string = "hola";
let b: string = "mundo";
let c = a - b;        // ERROR: '-' cannot be applied to strings
let d = a * b;        // ERROR: '*' cannot be applied to strings
let e: integer = 5;
let f: boolean = true;
let g = e + f;        // ERROR: cannot mix integer and boolean
