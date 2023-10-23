TEX = govardhan_cv.tex
PDF = govardhan_cv.pdf

.PHONY: all 
all: clean cv

.PHONY: cv
cv: $(TEX)
	pdflatex $(TEX)

.PHONY: all_view
view: 
	if [ -f $(PDF) ]; then
		evince $(PDF) &
	fi	

.PHONY: clean
clean:
	rm -rf log *.out


