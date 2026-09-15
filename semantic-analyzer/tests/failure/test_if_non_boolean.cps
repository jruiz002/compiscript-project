// test_if_non_boolean.cps
// EXPECTED ERROR: Non-boolean condition in control flow
let x: integer = 5;

if (x) {               // ERROR: condition must be boolean
  print("si");
}

while (x) {            // ERROR: condition must be boolean
  x = x - 1;
}

for (let i: integer = 0; i; i = i + 1) {  // ERROR: condition must be boolean
  print(i);
}
