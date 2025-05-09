#ifndef RENLOI_BINT_H
#define RENLOI_BINT_H

#ifdef __cplusplus
extern "C" {
#endif

void* bint_new();
void* bint_from_int(int val);
void* bint_from_string(const char* val);
void bint_delete(void* ptr);

void* bint_add(void* a, void* b);
void* bint_sub(void* a, void* b);
void* bint_mul(void* a, void* b);
void* bint_div(void* a, void* b);
void* bint_mod(void* a, void* b);

void* bint_neg(void* a);
void* bint_not(void* a);

void* bint_and(void* a, void* b);
void* bint_or(void* a, void* b);
void* bint_xor(void* a, void* b);
void* bint_lshift(void* a, int n);
void* bint_rshift(void* a, int n);

int bint_eq(void* a, void* b);
int bint_ne(void* a, void* b);
int bint_lt(void* a, void* b);
int bint_le(void* a, void* b);
int bint_gt(void* a, void* b);
int bint_ge(void* a, void* b);

int bint_to_int(void* a);
const char* bint_to_string(void* a);

#ifdef __cplusplus
}
#endif

#endif 