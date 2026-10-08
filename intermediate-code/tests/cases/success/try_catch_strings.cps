let lista: integer[] = [1, 2, 3];
try {
  print("antes");
  let peligro = lista[100];
  print("nunca");
} catch (err) {
  print("Error atrapado: " + err);
}
let activo: boolean = lista[0] == 1;
print("activo=" + activo + ", total=" + 3);
