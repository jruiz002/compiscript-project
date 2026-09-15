// test_control_flow.cps — if/else, while, for, do-while, switch
let x: integer = 10;

if (x > 5) {
  print("mayor a 5");
} else {
  print("menor o igual a 5");
}

// while loop
let i: integer = 0;
while (i < 3) {
  print(i);
  i = i + 1;
}

// for loop
for (let j: integer = 0; j < 5; j = j + 1) {
  if (j == 2) {
    continue;
  }
  if (j == 4) {
    break;
  }
  print(j);
}

// do-while
let k: integer = 0;
do {
  k = k + 1;
} while (k < 3);
print(k);

// switch
switch (x) {
  case 10:
    print("diez");
  case 20:
    print("veinte");
  default:
    print("otro");
}

// switch with break in each case
switch (x) {
  case 10:
    print("diez");
    break;
  case 20:
    print("veinte");
    break;
  default:
    print("otro");
    break;
}
