; --- sección de datos ---
str_0: "antes"
str_1: "nunca"
str_2: "Error atrapado: "
str_3: "activo="
str_4: "true"
str_5: "false"
str_6: ", total="

func main, 12
    lista = newarray 3
    lista[4] = 1
    lista[8] = 2
    lista[12] = 3
    try_begin L0
    print str_0
    boundscheck lista, 100    # boundscheck
    t0 = 100 * 4
    t0 = t0 + 4
    peligro = lista[t0]
    print str_1
    try_end
    goto L1
L0:
    err = get_exception
    t0 = tostr err
    t0 = concat str_2, t0
    print t0
L1:
    boundscheck lista, 0    # boundscheck
    t0 = 0 * 4
    t0 = t0 + 4
    t1 = lista[t0]
    activo = t1 == 1
    ifFalse activo goto L2
    t0 = str_4
    goto L3
L2:
    t0 = str_5
L3:
    t0 = concat str_3, t0
    t0 = concat t0, str_6
    t1 = tostr 3
    t0 = concat t0, t1
    print t0
    return
endfunc main
