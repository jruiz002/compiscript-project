func main, 4
    param 5
    t0 = call f_factorial, 1    # factorial n=1
    print t0
    return
endfunc main

func f_factorial, 4
    t0 = n <= 1
    ifFalse t0 goto L0
    return 1
L0:
    t0 = n - 1
    param t0
    t0 = call f_factorial, 1    # factorial n=1
    t0 = n * t0
    return t0
endfunc f_factorial
