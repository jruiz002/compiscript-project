// test_arrays.cps — Arrays, indexing, foreach
let notas: integer[] = [90, 85, 100, 78];
let primera: integer = notas[0];

print(primera);

foreach (nota in notas) {
  print(nota);
}

let matriz: integer[][] = [[1, 2, 3], [4, 5, 6]];
let elem: integer = matriz[0][1];
print(elem);

let textos: string[] = ["hola", "mundo", "compiscript"];
foreach (t in textos) {
  print(t);
}
