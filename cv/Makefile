TEX = govardhan_cv.tex
PDF = govardhan_cv.pdf

.PHONY: all 
all: clean cv

.PHONY: cv
cv: $(TEX)
	pdflatex $(TEX)

.PHONY: all_view
view: 
	evince $(PDF) &

.PHONY: clean
clean:
	rm -rf log *.out *.aux *.fdb* *.fls 
