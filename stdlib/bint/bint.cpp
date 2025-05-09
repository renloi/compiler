#include <iostream>
#include <gmpxx.h>
#include <regex>
#include <cstring>

class bint {
private:
    mpz_class value;

public:

    bint() : value(0) {}

    bint(int val) : value(val) {}

    bint(const char* val) {
        try {
            std::string strVal(val);
            std::regex hex_pattern("^0x[0-9a-fA-F]+$");
            std::regex decimal_pattern("^\\d+$");

            if (std::regex_match(strVal, hex_pattern)) {

                value = mpz_class(strVal.c_str() + 2, 16);
            } else if (std::regex_match(strVal, decimal_pattern)) {

                value = mpz_class(strVal);
            } else {

                try {
                    value = mpz_class(strVal);
                    fprintf(stderr, "Parsed as: %s\n", value.get_str().c_str());
                } catch (...) {

                    fprintf(stderr, "Error: Invalid string format '%s'. Defaulting to 0.\n", strVal.c_str());
                    value = 0;
                }
            }
        } catch (std::exception& e) {
            fprintf(stderr, "Exception parsing string: %s\n", e.what());
            value = 0;
        } catch (...) {
            fprintf(stderr, "Unknown exception parsing string\n");
            value = 0;
        }
    }

    bint operator+(int other) const {
        return *this + bint(other);
    }

    bint operator-(int other) const {
        return *this - bint(other);
    }

    bint operator*(int other) const {
        return *this * bint(other);
    }

    bint operator/(int other) const {
        return *this / bint(other);
    }

    operator int() const {
        return value.get_si();
    }

    bint operator+(const bint& other) const {
        bint result;
        result.value = value + other.value;
        return result;
    }

    bint operator-(const bint& other) const {
        bint result;
        result.value = value - other.value;
        return result;
    }

    bint operator*(const bint& other) const {
        bint result;
        result.value = value * other.value;
        return result;
    }

    bint operator/(const bint& other) const {
        if (other.value != 0) {
            bint result;
            result.value = value / other.value;
            return result;
        } else {

            std::cerr << "Error: Division by zero." << std::endl;
            return bint();
        }
    }

    bint& operator=(const bint& other) {
        value = other.value;
        return *this;
    }

    bint& operator++() {
        value++;
        return *this;
    }

    bint operator++(int) {
        bint temp = *this;
        ++(*this);
        return temp;
    }

    bint& operator--() {
        value--;
        return *this;
    }

    bint operator--(int) {
        bint temp = *this;
        --(*this);
        return temp;
    }

    bint& operator+=(const bint& other) {
        value += other.value;
        return *this;
    }

    bint& operator-=(const bint& other) {
        value -= other.value;
        return *this;
    }

    bint& operator*=(const bint& other) {
        value *= other.value;
        return *this;
    }

    bint& operator/=(const bint& other) {
        if (other.value != 0) {
            value /= other.value;
        } else {

            std::cerr << "Error: Division by zero." << std::endl;
            value = 0;
        }
        return *this;
    }

    bint operator-() const {
        bint result;
        result.value = -value;
        return result;
    }

    bint operator%(const bint& other) const {
        if (other.value != 0) {
            bint result;
            result.value = value % other.value;
            return result;
        } else {

            std::cerr << "Error: Modulus by zero." << std::endl;
            return bint();
        }
    }

    bint operator%(int other) const {
        if (other != 0) {
            bint result;
            result.value = value % other;
            return result;
        } else {

            std::cerr << "Error: Modulus by zero." << std::endl;
            return bint();
        }
    }

    bool operator==(const bint& other) const {
        return value == other.value;
    }

    bool operator!=(const bint& other) const {
        return value != other.value;
    }

    bool operator<(const bint& other) const {
        return value < other.value;
    }

    bool operator<=(const bint& other) const {
        return value <= other.value;
    }

    bool operator>(const bint& other) const {
        return value > other.value;
    }

    bool operator>=(const bint& other) const {
        return value >= other.value;
    }

    bint operator&(const bint& other) const {
        bint result;
        result.value = value & other.value;
        return result;
    }

    bint operator|(const bint& other) const {
        bint result;
        result.value = value | other.value;
        return result;
    }

    bint operator^(const bint& other) const {
        bint result;
        result.value = value ^ other.value;
        return result;
    }

    bint operator~() const {
        bint result;
        result.value = ~value;
        return result;
    }

    bint operator<<(int n) const {
        bint result;
        result.value = value << n;
        return result;
    }

    bint operator>>(int n) const {
        bint result;
        result.value = value >> n;
        return result;
    }

    bool operator&&(const bint& other) const {
        return value && other.value;
    }

    bool operator||(const bint& other) const {
        return value || other.value;
    }

    bool operator!() const {
        return !value;
    }

    bint& operator&=(const bint& other) {
        value &= other.value;
        return *this;
    }

    bint& operator|=(const bint& other) {
        value |= other.value;
        return *this;
    }

    bint& operator^=(const bint& other) {
        value ^= other.value;
        return *this;
    }

    bool operator==(const std::string& str) const {
        return value == mpz_class(str);
    }

    bool operator!=(const std::string& str) const {
        return value != mpz_class(str);
    }

    operator std::string() const {
        return value.get_str();
    }

    bool operator==(int other) const {
        return value == mpz_class(other);
    }

    bool operator!=(int other) const {
        return value != mpz_class(other);
    }

    bool operator<(int other) const {
        return value < mpz_class(other);
    }

    bool operator<=(int other) const {
        return value <= mpz_class(other);
    }

    bool operator>(int other) const {
        return value > mpz_class(other);
    }

    bool operator>=(int other) const {
        return value >= mpz_class(other);
    }

    bint modInverse(const bint& modulus) const {
        bint result;
        if (modulus.value == 0) {
            std::cerr << "Error: Modulus is zero. Modular inverse does not exist." << std::endl;
            return result; 
        }

        if (mpz_invert(result.value.get_mpz_t(), value.get_mpz_t(), modulus.value.get_mpz_t()) == 0) {
            result.value = 0;
        }

        return result;
    }

    friend std::ostream& operator<<(std::ostream& os, const bint& num) {
        os << num.value.get_str();
        return os;
    }

   friend std::istream& operator>>(std::istream& is, bint& num) {
       std::string input;
       is >> input;
       num = bint(input.c_str());
       return is;
   }

   std::string toString() const {
       return value.get_str();
   }
};

extern "C" {

    void* bint_new() {
        return new bint();
    }

    void* bint_from_int(int val) {
        return new bint(val);
    }

    void* bint_from_string(const char* val) {
        try {
            if (val == nullptr) {
                fprintf(stderr, "Error in bint_from_string: Received null pointer\n");
                return new bint(0);
            }

            std::string strVal(val);

            bint* result = nullptr;
            try {
                result = new bint(strVal.c_str());
                return result;
            } catch (const std::exception& e) {
                fprintf(stderr, "Exception creating bint from string: %s\n", e.what());
                return new bint(0);
            }
        } catch (std::exception& e) {
            fprintf(stderr, "Exception in bint_from_string: %s\n", e.what());
            return new bint(0);
        } catch (...) {
            fprintf(stderr, "Unknown exception in bint_from_string\n");
            return new bint(0);
        }
    }

    void bint_delete(void* ptr) {
        delete static_cast<bint*>(ptr);
    }

    void* bint_add(void* a, void* b) {
        bint* result = new bint();
        *result = *static_cast<bint*>(a) + *static_cast<bint*>(b);
        return result;
    }

    void* bint_sub(void* a, void* b) {
        bint* result = new bint();
        *result = *static_cast<bint*>(a) - *static_cast<bint*>(b);
        return result;
    }

    void* bint_mul(void* a, void* b) {
        bint* result = new bint();
        *result = *static_cast<bint*>(a) * *static_cast<bint*>(b);
        return result;
    }

    void* bint_div(void* a, void* b) {
        bint* result = new bint();
        *result = *static_cast<bint*>(a) / *static_cast<bint*>(b);
        return result;
    }

    void* bint_mod(void* a, void* b) {
        bint* result = new bint();
        *result = *static_cast<bint*>(a) % *static_cast<bint*>(b);
        return result;
    }

    void* bint_neg(void* a) {
        bint* result = new bint();
        *result = -(*static_cast<bint*>(a));
        return result;
    }

    void* bint_not(void* a) {
        bint* result = new bint();
        *result = ~(*static_cast<bint*>(a));
        return result;
    }

    void* bint_and(void* a, void* b) {
        bint* result = new bint();
        *result = *static_cast<bint*>(a) & *static_cast<bint*>(b);
        return result;
    }

    void* bint_or(void* a, void* b) {
        bint* result = new bint();
        *result = *static_cast<bint*>(a) | *static_cast<bint*>(b);
        return result;
    }

    void* bint_xor(void* a, void* b) {
        bint* result = new bint();
        *result = *static_cast<bint*>(a) ^ *static_cast<bint*>(b);
        return result;
    }

    void* bint_lshift(void* a, int n) {
        bint* result = new bint();
        *result = *static_cast<bint*>(a) << n;
        return result;
    }

    void* bint_rshift(void* a, int n) {
        bint* result = new bint();
        *result = *static_cast<bint*>(a) >> n;
        return result;
    }

    int bint_eq(void* a, void* b) {
        return *static_cast<bint*>(a) == *static_cast<bint*>(b);
    }

    int bint_ne(void* a, void* b) {
        return *static_cast<bint*>(a) != *static_cast<bint*>(b);
    }

    int bint_lt(void* a, void* b) {
        return *static_cast<bint*>(a) < *static_cast<bint*>(b);
    }

    int bint_le(void* a, void* b) {
        return *static_cast<bint*>(a) <= *static_cast<bint*>(b);
    }

    int bint_gt(void* a, void* b) {
        return *static_cast<bint*>(a) > *static_cast<bint*>(b);
    }

    int bint_ge(void* a, void* b) {
        return *static_cast<bint*>(a) >= *static_cast<bint*>(b);
    }

    int bint_to_int(void* a) {
        return static_cast<int>(*static_cast<bint*>(a));
    }

    const char* bint_to_string(void* a) {

        static char buffer[1024];

        std::string str = static_cast<std::string>(*static_cast<bint*>(a));

        if (str.length() < sizeof(buffer) - 1) {
            strcpy(buffer, str.c_str());
            return buffer;
        } else {

            strncpy(buffer, str.c_str(), sizeof(buffer) - 1);
            buffer[sizeof(buffer) - 1] = '\0';
            return buffer;
        }
    }

    void bint_print(void* a) {
        try {
            if (a == nullptr) {
                fprintf(stderr, "Error: Null pointer passed to bint_print\n");
                return;
            }

            bint* num = static_cast<bint*>(a);
            std::string str = num->toString();
            fprintf(stdout, "%s", str.c_str());
        } catch (std::exception& e) {
            fprintf(stderr, "Exception in bint_print: %s\n", e.what());
        } catch (...) {
            fprintf(stderr, "Unknown exception in bint_print\n");
        }
    }
}