#include "math.h"
#include <cmath>

#ifndef M_PI
#define M_PI 3.14159265358979323846
#endif

#ifndef M_E
#define M_E 2.71828182845904523536
#endif

float math_sin(float x) {
    return std::sin(x);
}

float math_cos(float x) {
    return std::cos(x);
}

float math_tan(float x) {
    return std::tan(x);
}

float math_sqrt(float x) {
    return std::sqrt(x);
}

float math_pow(float x, float y) {
    return std::pow(x, y);
}

float math_log(float x) {
    return std::log(x);
}

float math_exp(float x) {
    return std::exp(x);
}

float math_abs(float x) {
    return std::abs(x);
}

float math_floor(float x) {
    return std::floor(x);
}

float math_ceil(float x) {
    return std::ceil(x);
}

float math_round(float x) {
    return std::round(x);
}

float math_PI() {
    return M_PI;
}

float math_E() {
    return M_E;
} 