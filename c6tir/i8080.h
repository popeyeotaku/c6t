/* C6TIR Backend Header for Intel 8080/Zilog Z80 */

/* We use BC as the frame pointer, leaving DE and HL as the two
 * available 16bit registers. A is used as needed by templates.
 * Since nothing can be computed into DE that cannot also
 * be computed into HL, we always compute values into HL when
 * possible. The results of all expressions will end up in HL.
 *
 * When floating support is added, it will have to similar
 * virtual floating point registers in RAM, and will use the same
 * allocation algorithms.
 */

/* Codegen Template Difficulties */
#define DHL 0	/* Can be computed into HL directly */
#define DEITHER 1	/* Can be computed into HL or DE */
#define DBIN 2	/* Normal binary template requiring operands into
		 * HL and DE.
		 */
#define DSPECIAL 3	/* Assumes both registers used, requires
			 * special handling.
			 */

/* Codegen template */
struct templ {
	int tlab;	/* Matching node label */
	int tleft, tright;	/* Matching left/right node labels
				 * (0 if not matched)
				 */
	int tdiff;	/* Difficulty level */
	int tflags;	/* Various flags defined below */
	char *tstr;	/* Assembly code for match */
} templand[];
#define TLSKIP 01	/* Skip left child in output */
#define TRSKIP 02	/* Skip right child in output */
#define TCOMMUT 04	/* DBIN template where the order of the child
			 * templates (which register they end up in)
			 * does not matter.
			 */

/* Defines for the two registers */
#define HL 0
#define DE 1

int nextstatic;	/* Next temporary label */
