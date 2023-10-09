# Define the source and target files
SOURCE = govardhan_cv.tex
TARGET = govardhan_cv.pdf

# Build the PDF
all: $(TARGET)

cv: $(SOURCE)
	pdflatex $(SOURCE) 

# Clean up temporary files
clean:
	rm -f log *.out

.PHONY: all clean
