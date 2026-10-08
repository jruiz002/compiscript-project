let x: integer = 7;
if (x > 5 || x < 0) {
  print("fuera de [0,5]");
} else {
  print("dentro");
}
let i: integer = 0;
while (i < 3 && x != 0) {
  i = i + 1;
}
do {
  i = i - 1;
} while (i > 0);
for (let j: integer = 0; j < 4; j = j + 1) {
  if (j == 1) { continue; }
  if (j == 3) { break; }
  print(j);
}
switch (x) {
  case 1:
    print("uno");
  case 7:
    print("siete");
  default:
    print("default");
}
let signo = x > 0 ? "positivo" : "no positivo";
print(signo);
