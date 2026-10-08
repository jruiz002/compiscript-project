function suma(a: integer[]): integer {
  let total: integer = 0;
  foreach (n in a) {
    if (n < 0) { continue; }
    total = total + n;
  }
  return total;
}
let notas: integer[] = [90, -1, 85, 100];
print(suma(notas));
let matriz: integer[][] = [[1, 2], [3, 4]];
matriz[1][0] = matriz[0][1] * 10;
print(matriz[1][0]);
foreach (fila in matriz) {
  foreach (v in fila) {
    print(v);
  }
}
