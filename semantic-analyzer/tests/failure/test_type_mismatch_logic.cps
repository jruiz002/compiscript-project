// test_type_mismatch_logic.cps
// EXPECTED ERROR: Logical operators require boolean operands
let a: integer = 5;
let b: integer = 3;
let c = a && b;      // ERROR: '&&' requires boolean operands
let d = a || b;      // ERROR: '||' requires boolean operands
let e = !a;          // ERROR: '!' requires boolean operand
