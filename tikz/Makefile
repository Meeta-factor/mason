CSV := $(wildcard *.csv)
TEX := $(CSV:.csv=.tex)
PDF := $(CSV:.csv=.pdf)

all: $(PDF)

%.tex: %.csv mason_build.py
	python mason_build.py $<

%.pdf: %.tex
	pdflatex -interaction=nonstopmode $<

clean:
	rm -f *.aux *.log *.tex *.pdf