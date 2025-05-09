#ifndef RENLOI_MATH_H
#define RENLOI_MATH_H

#ifdef __cplusplus
extern "C" {
#endif

float math_sin(float x);
float math_cos(float x);
float math_tan(float x);
float math_sqrt(float x);
float math_pow(float x, float y);
float math_log(float x);
float math_exp(float x);
float math_abs(float x);
float math_floor(float x);
float math_ceil(float x);
float math_round(float x);
float math_PI();
float math_E();

#ifdef __cplusplus
}
#endif

#endif 