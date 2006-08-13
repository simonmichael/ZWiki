swig -python texbreaker.i
gcc -fpic -c texbreaker.c texbreaker_wrap.c -I/usr/include/python2.3
ld -shared texbreaker.o texbreaker_wrap.o -o _texbreaker.so