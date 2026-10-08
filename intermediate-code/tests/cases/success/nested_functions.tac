func main, 8
    param 10
    t0 = call f_contador, 1    # contador n=1
    print t0
    return
endfunc main

func f_contador, 8
    cuenta = inicio
    param fp
    param 3
    call f_contador__repetir, 2    # repetir n=2
    return cuenta
endfunc f_contador

func f_contador__incrementar, 8
    t0 = up 1, -8    # up cuenta
    t0 = t0 + k
    up 1, -8 = t0    # up cuenta =
    return
endfunc f_contador__incrementar

func f_contador__repetir, 12
    if n <= 0 goto L0
    t0 = up 0, -4    # static link +1
    param t0
    param n
    call f_contador__incrementar, 2    # incrementar n=2
    t0 = n - 1
    t1 = up 0, -4    # static link +1
    param t1
    param t0
    call f_contador__repetir, 2    # repetir n=2
L0:
    return
endfunc f_contador__repetir
