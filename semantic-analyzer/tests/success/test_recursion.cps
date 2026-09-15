// test_recursion.cps — Recursive functions
function factorial(n: integer): integer {
  if (n <= 1) {
    return 1;
  }
  return n * factorial(n - 1);
}

function fibonacci(n: integer): integer {
  if (n <= 1) {
    return n;
  }
  return fibonacci(n - 1) + fibonacci(n - 2);
}

let f5: integer = factorial(5);
let fib10: integer = fibonacci(10);

print(f5);
print(fib10);
