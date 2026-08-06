# Documento final

Esta carpeta contiene el documento académico final de Mitotl IA en LaTeX.

## Archivos

- `documento_final.tex`: fuente principal editable.
- `referencias.bib`: referencias bibliográficas en formato BibLaTeX.
- `figuras/`: imágenes y evidencias que se incorporarán al documento.
- `00-estrategia.md`: antecedente de decisiones del proyecto.

## Compilación

Requiere una instalación de LaTeX con `pdflatex`, `biber` y los paquetes usados por el documento.

```bash
latexmk -pdf -interaction=nonstopmode -halt-on-error documento_final.tex
```

La compilación genera `documento_final.pdf` en esta carpeta. Para limpiar archivos auxiliares:

```bash
latexmk -C documento_final.tex
```

## Versiones de documentación

- V0: estructura, portada editable, bibliografía base y diagrama del pipeline.
- V1: problema, estrategia y datos.
- V2: EDA, variables, modelación y pipeline.
- V3: resultados, interfaz y limitaciones.
- V4: revisión de rúbrica, referencias y versión final.
