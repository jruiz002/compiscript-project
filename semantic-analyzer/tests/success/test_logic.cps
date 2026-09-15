// test_logic.cps — Valid logical operations
let a: boolean = true;
let b: boolean = false;

let c: boolean = a && b;
let d: boolean = a || b;
let e: boolean = !a;
let f: boolean = !b && a;
let g: boolean = (a || b) && !(a && b);

print(c);
print(d);
print(g);
