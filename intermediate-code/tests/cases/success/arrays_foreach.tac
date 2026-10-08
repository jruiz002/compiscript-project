func main, 16
    notas = newarray 4
    notas[4] = 90
    t0 = -1
    notas[8] = t0
    notas[12] = 85
    notas[16] = 100
    param notas
    t0 = call f_suma, 1    # suma n=1
    print t0
    matriz = newarray 2
    t0 = newarray 2
    t0[4] = 1
    t0[8] = 2
    matriz[4] = t0
    t0 = newarray 2
    t0[4] = 3
    t0[8] = 4
    matriz[8] = t0
    boundscheck matriz, 0    # boundscheck
    t0 = 0 * 4
    t0 = t0 + 4
    t1 = matriz[t0]
    boundscheck t1, 1    # boundscheck
    t0 = 1 * 4
    t0 = t0 + 4
    t2 = t1[t0]
    t0 = t2 * 10
    boundscheck matriz, 1    # boundscheck
    t1 = 1 * 4
    t1 = t1 + 4
    t2 = matriz[t1]
    boundscheck t2, 0    # boundscheck
    t1 = 0 * 4
    t1 = t1 + 4
    t2[t1] = t0
    boundscheck matriz, 1    # boundscheck
    t0 = 1 * 4
    t0 = t0 + 4
    t1 = matriz[t0]
    boundscheck t1, 0    # boundscheck
    t0 = 0 * 4
    t0 = t0 + 4
    t2 = t1[t0]
    print t2
    __arr = matriz
    __idx = 0
    __len = len __arr
L4:
    if __idx >= __len goto L6
    t0 = __idx * 4
    t0 = t0 + 4
    fila = __arr[t0]
    __arr = fila
    __idx = 0
    __len = len __arr
L7:
    if __idx >= __len goto L9
    t0 = __idx * 4
    t0 = t0 + 4
    v = __arr[t0]
    print v
L8:
    __idx = __idx + 1
    goto L7
L9:
L5:
    __idx = __idx + 1
    goto L4
L6:
    return
endfunc main

func f_suma, 28
    total = 0
    __arr = a
    __idx = 0
    __len = len __arr
L0:
    if __idx >= __len goto L2
    t0 = __idx * 4
    t0 = t0 + 4
    n = __arr[t0]
    if n >= 0 goto L3
    goto L1
L3:
    total = total + n
L1:
    __idx = __idx + 1
    goto L0
L2:
    return total
endfunc f_suma
