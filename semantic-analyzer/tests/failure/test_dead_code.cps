// test_dead_code.cps
// EXPECTED WARNING: Unreachable code after return
function foo(): integer {
  return 1;
  let x: integer = 5;     // WARNING: unreachable
  print(x);               // WARNING: unreachable
}

function bar(): integer {
  let i: integer = 0;
  while (i < 10) {
    if (i == 5) {
      break;
      print(i);           // WARNING: unreachable
    }
    i = i + 1;
  }
  return i;
}
