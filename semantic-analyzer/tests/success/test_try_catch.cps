// test_try_catch.cps — try/catch
let lista: integer[] = [1, 2, 3];

try {
  let x: integer = lista[0];
  print(x);
} catch (err) {
  print("Error: " + err);
}
