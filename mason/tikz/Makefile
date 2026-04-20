CSV := $(wildcard *.csv)
TEX := $(CSV:.csv=.tex)
PDF := $(CSV:.csv=.pdf)
PNG := $(CSV:.csv=.png)

.SECONDARY: $(TEX)

all: $(PNG)

%.tex: %.csv mason_build.py
	python mason_build.py $<

%.pdf: %.tex
	pdflatex -interaction=nonstopmode -halt-on-error $<
	pdflatex -interaction=nonstopmode -halt-on-error $<

%.png: %.pdf
	pdftoppm -png -r 300 $< temp
	mv temp-1.png $@

clean:
	rm -f *.aux *.log *.tex *.pdf *.png temp-*.png