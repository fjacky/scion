#include <stdlib.h>
#include <string.h>
#include <limits.h>
#include <math.h>
#include <stdint.h>

#include "aesni.h"


#if (INT_MAX != 0x7fffffff)
#error -- Assumes 4-byte int
#endif


void *malloc_aligned(size_t alignment, size_t bytes)
{
    const size_t total_size = bytes + (2 * alignment) + sizeof(size_t);

    // use malloc to allocate the memory.
    char *data = malloc(sizeof(char) * total_size);

    if (data)
    {
        // store the original start of the malloc'd data.
        const void * const data_start = data;

        // dedicate enough space to the book-keeping.
        data += sizeof(size_t);

        // find a memory location with correct alignment. the alignment minus
        // the remainder of this mod operation is how many bytes forward we need
        // to move to find an aligned byte.
        const size_t offset = alignment - (((size_t)data) % alignment);

        // set data to the aligned memory.
        data += offset;

        // write the book-keeping.
        size_t *book_keeping = (size_t*)(data - sizeof(size_t));
        *book_keeping = (size_t)data_start;
    }

    return data;
}

void free_aligned(void *raw_data)
{
    if (raw_data)
    {
        char *data = raw_data;

        // we have to assume this memory was allocated with malloc_aligned.
        // this means the sizeof(size_t) bytes before data are the book-keeping
        // which points to the location we need to pass to free.
        data -= sizeof(size_t);

        // set data to the location stored in book-keeping.
        data = (char*)(*((size_t*)data));

        // free the memory.
        free(data);
    }
}

unsigned char* aes_assembly_init(void *enc_key)
{
    if (enc_key != NULL) {
    	unsigned char* roundkey = (unsigned char*)malloc_aligned(16, 10*16*sizeof(char));
    	memset(roundkey, 0, sizeof(10*16*sizeof(char)));
    	ExpandKey128(enc_key, roundkey);
    	return roundkey;
    }
}



int main()
{
/*
	// openssl enc -e -aes-128-cbc -K 000102030405060708090a0b0c0d0e0f -iv 00000000000000000000000000000000 < file -nopad | hexdump -C
	


	// openssl enc -e -aes-128-cbc -K 06a9214036b8a15b512e03d534120006 -iv 00000000000000000000000000000000 < file -nopad | hexdump -C
	// 3a e0 0f bd 31 df ae ed  4d a6 e4 4f e2 c1 1b 4f
	unsigned long long start, end;
	int i, j;
	struct keystruct rk;
	//unsigned char key[] = {0x01,0x23,0x45,0x67,0x89,0xab,0xcd,0xef}; //"0123456789abcdef";
	//unsigned char key[] = {0x06,0xa9,0x21,0x40,0x36,0xb8,0xa1,0x5b,0x51,0x2e,0x03,0xd5,0x34,0x12,0x00,0x06}; //"0123456789abcdef";
	unsigned char key[] = {0x00,0x01,0x02,0x03,0x04,0x05,0x06,0x07,0x08,0x09,0x0A,0x0B,0x0C,0x0D,0x0E,0x0F}; //"0123456789abcdef";
		
	rk.roundkey = aes_assembly_init(key);

	for(i=0;i<=10;i++)
	{
		printf("roundkey[%d]:", i);
		for(j=0;j<16;j++) printf("%2x", rk.roundkey[i*16+j]);
		printf("\n");
	}

	//int blk = 21;
	int blk = 1;
	//unsigned char input[16*blk];
//	unsigned char input[] = "Single block msg"; //"0123456789abcdef";
	unsigned char input[] = {0x00,0x11,0x22,0x33,0x44,0x55,0x66,0x77,0x88,0x99,0xaa,0xbb,0xcc,0xdd,0xee,0xff}; //"0123456789abcdef";
	

	//unsigned char input[] = "0123456789abcdef";
	unsigned char mac[16];
	//unsigned char random[16*blk];
	rk.iv = malloc(16*sizeof(char));

	
	// for testing
	//for(i=0;i<16*blk;i++) input[i] = i;

	
	printf("input: ");
	i=0;
	for(j=0;j<16;j++)
		printf("%2x", input[i*16+j]);
	printf("\n");
	
	CBCMAC(rk.roundkey, blk, input, mac);
	
	printf("MAC: ");	
	for(j=0;j<16;j++)
		printf("%2x", mac[i*16+j]);
	printf("\n");


*/
	unsigned long long start, end;
	int i, j;
	struct keystruct rk;
	unsigned char key[] = {0x00,0x00,0x00,0x00,0x00,0x00,0x00,0x00,0x00,0x00,0x00,0x00,0x00,0x00,0x00,0x00};
	rk.roundkey = aes_assembly_init(key);

	for(i=0;i<10;i++)
	{
		printf("roundkey[%d]:", i);
		for(j=0;j<16;j++) printf("%2x", rk.roundkey[i*16+j]);
		printf("\n");
	}

	//int blk = 21;
	int blk = 2;
	unsigned char input[] = {0x6a,0x84,0x86,0x7c,0xd7,0x7e,0x12,0xad,0x07,0xea,0x1b,0xe8,0x95,0xc5,0x3f,0xa3,0x6a,0x84,0x86,0x7c,0xd7,0x7e,0x12,0xad,0x07,0xea,0x1b,0xe8,0x95,0xc5,0x3f,0xaa};
	unsigned char mac[32];
	unsigned char random[16*blk];
	//rk.iv = malloc(16*sizeof(char));

	
	// for testing
	//for(i=0;i<16*blk;i++) input[i] = i;

	
	printf("input: ");
	for (i = 0; i < blk; i++){
		for(j=0;j<16;j++)
			printf("%2x", input[i*16+j]);
		printf("\n");
	}
	
	CBCMAC(rk.roundkey, blk, input, mac);
	
	
	printf("MAC: ");	
	i=0;
		for(j=0;j<16;j++)
			printf("%2x", mac[i*16+j]);
		printf("\n");
	
	//for(i=0;i<100000;i++) CBCMAC(rk.roundkey, blk, input, mac);

	//unsigned long long t1 = _do_rdtsc();
	//for(i=0;i<100000;i++) CBCMAC(rk.roundkey, blk, input, mac);
	//unsigned long long t2 = _do_rdtsc();

	//printf("cycle(CBC) = %f\n", (double)(t2-t1)/100000);

	//t1 = _do_rdtsc();
	//for(i=0;i<100000;i++) PMAC(rk.roundkey, blk, input, mac);
	//t2 = _do_rdtsc();

	//printf("cycle(PCBC) = %f\n", (double)(t2-t1)/100000);

	//blk = 4;
	//PRF(rk.roundkey, blk, input, random);

	//printf("random:");
	//for(i=0;i<4;i++){
	//	for(j=0;j<16;j++)
	//		printf("%2x", random[i*16+j]);
	//	printf("\n");
	//}
	//printf("\n");

	free_aligned(rk.roundkey);
	//free(rk.iv);
	return 0;
}

