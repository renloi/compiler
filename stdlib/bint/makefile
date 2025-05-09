CXX = clang++
CXXFLAGS = -fPIC -std=c++17 -Wall -I.
LDFLAGS = -shared -lgmp -lgmpxx

TARGET = libbint.so
BC_TARGET = bint.bc
SRCS = bint.cpp

all: $(TARGET) $(BC_TARGET)

$(TARGET): $(SRCS)
	$(CXX) $(CXXFLAGS) -o $@ $^ $(LDFLAGS)

$(BC_TARGET): $(SRCS)
	clang++ -emit-llvm -c -o $@ $^ $(CXXFLAGS)

clean:
	rm -f $(TARGET) $(BC_TARGET)

.PHONY: all clean 