/*
 ****************************************************************************
 *
 * MODULE:       r.pi.prob.mw
 * AUTHOR(S):    Elshad Shirinov, Dr. Martin Wegmann
 * PURPOSE:      Probability analysis of 2 randomly set points to be 
 *              located within the same patch - patch-to-patch distance setting optional
 *
 * COPYRIGHT:    (C) 2009-2011 by the GRASS Development Team
 *
 *               This program is free software under the GNU General Public
 *               License (>=v2). Read the file COPYING that comes with GRASS
 *               for details.
 *
 *****************************************************************************/

#define MAIN

#include "local_proto.h"

struct statmethod
{
    f_statmethod *method;	/* routine to compute new value */
    char *name;			/* method name */
    char *text;			/* menu display - full description */
    char *suffix;		/* output suffix */
};

static struct statmethod statmethods[] = {
    {average, "average", "average of values", "avg"},
    {variance, "variance", "variance of values", "var"},
    {std_deviat, "standard deviation", "standard deviation of values", "dev"},
    {median, "median", "median of values", "med"},
    {min, "min", "minimum of values", "min"},
    {max, "max", "maximum of values", "max"},
    {0, 0, 0, 0}
};

int main(int argc, char *argv[])
{
    /* input */
    char *oldname, *oldmapset;
    /* output */
    char *newname, *newmapset;
    /* mask */
    char *maskname, *maskmapset;
    /* in and out file pointers */
    int in_fd, out_fd;
    /* parameters */
    int stats[GNAME_MAX];
    f_statmethod *methods;
    int stat_count;
    int keyval;
    int n;
    int size;
    double distance;
    int patch_only;

    /* maps */
    int *map;
    int *mask;

    /* other parameters */
    char *title;

    /* helper variables */
    int row, col;
    CELL *result;
    DCELL *d_res;
    DCELL *values;
    int i, j;
    Coords *p;
    char *str;
    int method;
    char outname[GNAME_MAX];
    int nx, ny;

    RASTER_MAP_TYPE map_type;
    struct Cell_head ch, window;

    struct GModule *module;
    struct
    {
	struct Option *input, *output, *mask;
	struct Option *keyval, *n;
	struct Option *size, *distance;
    } parm;
    struct
    {
	struct Flag *patch_only;
    } flag;

    G_gisinit(argv[0]);

    module = G_define_module();
    module->keywords = _("raster");
    module->description =
	_("Probability analysis of 2 random points being in the same patch.");

    parm.input = G_define_standard_option(G_OPT_R_INPUT);

    parm.output = G_define_standard_option(G_OPT_R_OUTPUT);

    parm.mask = G_define_option();
    parm.mask->key = "mask";
    parm.mask->type = TYPE_STRING;
    parm.mask->required = NO;
    parm.mask->gisprompt = "old,cell,raster";
    parm.mask->description = _("Name of the mask raster file");

    parm.keyval = G_define_option();
    parm.keyval->key = "keyval";
    parm.keyval->type = TYPE_INTEGER;
    parm.keyval->required = YES;
    parm.keyval->description = _("Category value of the patches");

    parm.n = G_define_option();
    parm.n->key = "n";
    parm.n->type = TYPE_INTEGER;
    parm.n->required = YES;
    parm.n->description = _("Number of tests");

    parm.size = G_define_option();
    parm.size->key = "size";
    parm.size->type = TYPE_INTEGER;
    parm.size->required = NO;
    parm.size->description = _("Size of the output matrix");

    parm.distance = G_define_option();
    parm.distance->key = "distance";
    parm.distance->type = TYPE_INTEGER;
    parm.distance->required = NO;
    parm.distance->description =
	_("Maximum distance at which two patches are seen as one");

    flag.patch_only = G_define_flag();
    flag.patch_only->key = 'p';
    flag.patch_only->description =
	_("Patch only flag. When set only places test-points in patches");

    if (G_parser(argc, argv))
	exit(EXIT_FAILURE);

    /* initialize random generator */
    srand(time(NULL));

    /* get name of input file */
    oldname = parm.input->answer;

    /* test input files existance */
    oldmapset = G_find_cell2(oldname, "");
    if (oldmapset == NULL)
        G_fatal_error(_("Raster map <%s> not found"), oldname);

    /* get name of mask */
    maskname = parm.mask->answer;

    /* test costmap existance */
    if (maskname && (maskmapset = G_find_cell2(maskname, "")) == NULL)
	        G_fatal_error(_("Raster map <%s> not found"), maskname);

    /* get keyval */
    sscanf(parm.keyval->answer, "%d", &keyval);

    /* get n */
    sscanf(parm.n->answer, "%d", &n);

    /* get size */
    if (parm.size->answer) {
	sscanf(parm.size->answer, "%d", &size);
    }
    else {
	size = 0;
    }

    /* get distance */
    if (parm.distance->answer) {
	sscanf(parm.distance->answer, "%lf", &distance);
    }
    else {
	distance = 1;
    }

    /* get patch_only */
    patch_only = flag.patch_only->answer;

    /* check if the new file name is correct */
    newname = parm.output->answer;
    if (G_legal_filename(newname) < 0)
	G_fatal_error(_("<%s> is an illegal file name"), newname);
    newmapset = G_mapset();

    map_type = DCELL_TYPE;

    /* get size */
    sx = G_window_cols();
    sy = G_window_rows();

    /* test output */
    /*      G_message("TEST OUTPUT :");
       G_message("input = %s", oldname);
       G_message("output = %s", newname);
       G_message("mask = %s", maskname);
       G_message("keyval = %d", keyval);    
       G_message("n = %d", n);
       G_message("size = %d", size);
       G_message("distance = %0.2f", distance);
       G_message("patch_only = %d", patch_only); */

    /* allocate map buffers */
    map = (int *)G_malloc(sx * sy * sizeof(int));
    mask = (int *) G_malloc(sx * sy * sizeof(int));
    cells = (Coords *) G_malloc(sx * sy * sizeof(Coords));

    result = G_allocate_c_raster_buf();
    d_res = G_allocate_d_raster_buf();

    fragments = (Coords **) G_malloc(sx * sy * sizeof(Coords *));
    fragments[0] = cells;

    nx = size > 0 ? sx - size + 1 : 1;
    ny = size > 0 ? sy - size + 1 : 1;
    values = (DCELL *) G_malloc(nx * ny * sizeof(Coords));

    /* open map */
    in_fd = G_open_cell_old(oldname, oldmapset);
    if (in_fd < 0)
	    G_fatal_error(_("Unable to open raster map <%s>"), oldname);

    /* read map */
    G_message("Reading map:");
    for (row = 0; row < sy; row++) {
	G_get_c_raster_row(in_fd, result, row);
	for (col = 0; col < sx; col++) {
	    if (result[col] == keyval)
		map[row * sx + col] = 1;
	}

	G_percent(row, sy, 2);
    }
    G_percent(1, 1, 2);

    /* close map */
    G_close_cell(in_fd);

    /* test output */
    /*      G_message("map:\n");
       print_buffer(map, sx, sy); */

    /* if mask specified, read mask */
    if (maskname) {
	/* open mask file */
	in_fd = G_open_cell_old(maskname, maskmapset);
	if (in_fd < 0)
	    G_fatal_error(_("Unable to open raster map <%s>"), maskname);

	/* read mask */
	G_message("Reading mask file:");
	for (row = 0; row < sy; row++) {
	    G_get_c_raster_row(in_fd, result, row);
	    for (col = 0; col < sx; col++) {
		mask[row * sx + col] = result[col];
	    }

	    G_percent(row, sy, 2);
	}
	G_percent(1, 1, 2);

	/* close mask */
	G_close_cell(in_fd);
    }
    else {
	/* if no costmap specified, fill mask with 1 */
	for (i = 0; i < sx * sy; i++) {
	    mask[i] = 1;
	}
    }

    /* test output */
    /*      G_message("costmap:\n");
       print_d_buffer(costmap, sx, sy); */

    /* find fragments */
    writeFragments(map, sy, sx, distance);

    /* test output */
    /*      G_message("fragcount = %d", fragcount);
       print_fragments(); */

    /* mark each fragment with its number */
    for (i = 0; i < sx * sy; i++) {
	map[i] = -1;
    }
    for (i = 0; i < fragcount; i++) {
	for (p = fragments[i]; p < fragments[i + 1]; p++) {
	    map[p->y * sx + p->x] = i;
	}
    }

    G_message("Performing analysis:");

    perform_analysis(values, map, mask, n, size, patch_only);

    /* test output */
    /*G_message("Values: ");
       for(j = 0; j < ny; j++) {
       for(i = 0; i < nx; i++) {
       fprintf(stderr, "%0.2f ", values[j * nx + i]);
       }
       fprintf(stderr, "\n");
       } */

    if (size > 0) {
	G_message("Writing output...");

	/* open the new cellfile  */
	out_fd = G_open_raster_new(newname, map_type);
	if (out_fd < 0)
	    G_fatal_error(_("Cannot create raster map <%s>"), newname);

	/* write the output file */
	for (row = 0; row < sy; row++) {
	    G_set_d_null_value(d_res, sx);

	    if (row >= size / 2 && row < ny + size / 2) {
		for (col = 0; col < nx; col++) {
		    d_res[col + size / 2] =
			values[(row - size / 2) * nx + col];
		}
	    }

	    G_put_d_raster_row(out_fd, d_res);

	    G_percent(row + 1, sy, 1);
	}

	/* close output */
	G_close_cell(out_fd);

    }
    else {
	fprintf(stdout, "\n\noutput = %lf\n\n", values[0]);
    }

    /* free allocated resources */
    G_free(map);
    G_free(mask);
    G_free(cells);
    G_free(fragments);

    exit(EXIT_SUCCESS);
}
