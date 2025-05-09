CXX = clang++
CXXFLAGS = -Wall -std=c++11 -emit-llvm -c -O2
LLVM_LINK = llvm-link

MODULE_NAME = math
SRC = $(MODULE_NAME).cpp
OBJ = $(MODULE_NAME).bc
TEMP_FILES = *.o *.ll *.s

all: $(OBJ)

$(OBJ): $(SRC)
	$(CXX) $(CXXFLAGS) -o $@ $<
	@rm -f $(TEMP_FILES)

clean:
	rm -f $(OBJ) $(TEMP_FILES) 