// test_for_non_boolean.cps
// EXPECTED ERROR: Condition in 'for' must be boolean

// ERROR: condición entera — no es boolean
for (let i: integer = 0; i; i = i + 1) {
  print(i);
}

// ERROR: condición string — no es boolean
for (let j: integer = 0; "continuar"; j = j + 1) {
  print(j);
}

// ERROR: condición float — no es boolean
let limite: float = 3.14;
for (let k: integer = 0; limite; k = k + 1) {
  print(k);
}
