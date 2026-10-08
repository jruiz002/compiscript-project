; --- sección de datos ---
str_0: " hace ruido."
str_1: " ladra."
str_2: "Toby"

func main, 8
    t0 = new Perro, 8
    param t0
    param str_2
    call Animal_constructor, 2    # n=2
    a = t0
    param a
    t0 = vcall a, 1    # .hablar n=1
    print t0
    return
endfunc main

func Animal_constructor, 4
    this[4] = nombre    # .nombre
    return
endfunc Animal_constructor

func Animal_hablar, 8
    t0 = this[4]    # .nombre
    t0 = concat t0, str_0
    return t0
endfunc Animal_hablar

func Perro_hablar, 8
    t0 = this[4]    # .nombre
    t0 = concat t0, str_1
    return t0
endfunc Perro_hablar
