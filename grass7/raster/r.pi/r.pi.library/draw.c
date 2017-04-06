#include "r_pi.h"

inline void swap(int *a, int *b)
{
    int zw = *a;

    *a = *b;
    *b = zw;
}

void draw_point(int *map, int val, int x, int y, int sx, int sy, int width)
{
    if (width <= 0) {
	return;
    }

    if (width == 1) {
	map[y * sx + x] = val;
    }
    else {
    }
}

void draw_line(int *map, int val, int x1, int y1, int x2, int y2, int sx,
	       int sy, int width)
{
    int steep = abs(y2 - y1) > abs(x2 - x1);

    if (steep) {
	swap(&x1, &y1);
	swap(&x2, &y2);
    }

    if (x1 > x2) {
	swap(&x1, &x2);
	swap(&y1, &y2);
    }

    int deltax = x2 - x1;
    int deltay = abs(y2 - y1);
    int error = deltax / 2;
    int ystep = y1 < y2 ? 1 : -1;
    int x;
    int y = y1;

    for (x = x1; x <= x2; x++) {
	if (steep) {
	    draw_point(map, val, y, x, sx, sy, width);
	}
	else {
	    draw_point(map, val, x, y, sx, sy, width);
	}

	error -= deltay;
	if (error < 0) {
	    y += ystep;
	    error += deltax;
	}
    }
}
