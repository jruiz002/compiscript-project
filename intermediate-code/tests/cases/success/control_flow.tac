; --- sección de datos ---
str_0: "fuera de [0,5]"
str_1: "dentro"
str_2: "uno"
str_3: "siete"
str_4: "default"
str_5: "positivo"
str_6: "no positivo"

func main, 4
    x = 7
    if x > 5 goto L2
    if x >= 0 goto L0
L2:
    print str_0
    goto L1
L0:
    print str_1
L1:
    i = 0
L3:
    if i >= 3 goto L4
    if x == 0 goto L4
    i = i + 1
    goto L3
L4:
L5:
    i = i - 1
L6:
    if i > 0 goto L5
L7:
    j = 0
L8:
    if j >= 4 goto L10
    if j != 1 goto L11
    goto L9
L11:
    if j != 3 goto L12
    goto L10
L12:
    print j
L9:
    j = j + 1
    goto L8
L10:
    if x == 1 goto L14
    if x == 7 goto L15
    goto L16
L14:
    print str_2
L15:
    print str_3
L16:
    print str_4
L13:
    if x <= 0 goto L17
    signo = str_5
    goto L18
L17:
    signo = str_6
L18:
    print signo
    return
endfunc main
