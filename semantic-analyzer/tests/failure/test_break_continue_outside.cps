// test_break_continue_outside.cps
// EXPECTED ERROR: break/continue used outside loops
break;           // ERROR
continue;        // ERROR

function foo() {
  break;         // ERROR: not inside a loop
}

// 'continue' is not valid inside a switch that isn't itself inside a loop
// ('break' inside a switch IS valid — see tests/success/test_control_flow.cps)
let x: integer = 1;
switch (x) {
  case 1:
    continue;    // ERROR: not inside a loop
}
