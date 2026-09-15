// test_arithmetic.cps — Valid arithmetic operations
let a: integer = 10;
let b: integer = 3;
let c: integer = a + b;       // integer + integer = integer
let d: integer = a - b;
let e: integer = a * b;
let f: integer = a / b;
let g: integer = a % b;

let x: float = 3.14;
let y: float = x * 2.0;      // float * float = float

let z: float = a + x;        // integer + float = float

let result: integer = (a + b) * (a - b);

print(c);
print(y);
