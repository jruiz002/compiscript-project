function contador(inicio: integer): integer {
  let cuenta: integer = inicio;
  function incrementar(k: integer) {
    cuenta = cuenta + k;
  }
  function repetir(n: integer) {
    if (n > 0) {
      incrementar(n);
      repetir(n - 1);
    }
  }
  repetir(3);
  return cuenta;
}
print(contador(10));
