// test_closures.cps — Nested functions (closures)
function crearContador(): integer {
  let cuenta: integer = 0;

  function incrementar(): integer {
    cuenta = cuenta + 1;
    return cuenta;
  }

  return incrementar();
}

let valor: integer = crearContador();
print(valor);

function outer(x: integer): integer {
  function inner(y: integer): integer {
    return x + y;   // captures x from outer scope
  }
  return inner(5);
}

let res: integer = outer(10);
print(res);
