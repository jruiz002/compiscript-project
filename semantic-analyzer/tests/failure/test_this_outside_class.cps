// test_this_outside_class.cps
// EXPECTED ERROR: 'this' used outside of a class
function foo() {
  this.nombre = "error";   // ERROR
}

let x = this;              // ERROR
