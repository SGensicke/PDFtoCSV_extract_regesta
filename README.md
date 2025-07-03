# PDFtoCSV_extract_regesta
The goal of this Jupyter notebook is to extract retro-digitised and OCR-processed regesta — for example, from the volumes of the Göttinger Papsturkundenwerk — into a structured tabular format, enabling their digital analysis. It was developed as part of the Academy project [Die Formierung Europas durch Überwindung der Spaltung im 12. Jahrhundert](https://formierung-europas.badw.de/).

The script takes advantage of the standardised layout of the printed editions to identify the individual components of each regest. It uses the Python library PyMuPDF to extract text line by line. As an initial step, the positions of blocks and lines can be visualised to manually define the page regions for the header, footer, page number, regesta number, date, and paragraph indentation — while accounting for whether the page is even or odd. To view the interactive visualisations generated with plotly (which do not render on GitHub), you can open the notebook with [nbviewer](https://nbviewer.org/github/SGensicke/PDFtoCSV_extract_regesta/blob/main/PDFtoCSV_extract_regesta-public.ipynb).

To minimize distortion, the pages are aligned at the upper left intersection of the type area. Each line is then assigned to a category based on its position. Finally, the processed data is compiled into a table. A Regestennummer always marks the start of a new entry, and the final table is saved as a CSV file. The main challenges arise from OCR errors, which often result in inconsistent spans, lines, and blocks, leading to misclassifications — especially when differentiating between italicised Kopfregesten, archival references, commentary, the main text, and footnotes. Manual corrections are therefore often necessary.

The code can be adapted for other regesta layouts — for instance, when the date is centered below the number, or when the number appears on the left and the date on the right of the same line. In general, the clearer the visual structure of the source text, the more accurate the results.

This tool was developed with the help of ChatGPT.

### Example page, plot of line midpoints
![](https://github.com/SGensicke/PDFtoCSV_extract_regesta/blob/main/images/example_page_PUU_Frankreich_I.png "example page") ![](https://github.com/SGensicke/PDFtoCSV_extract_regesta/blob/main/images/plot_line_midpoints_of_50_left_pages.png)

### Plotted lines of the example page, manually defined areas of interest and classified text parts
![](https://github.com/SGensicke/PDFtoCSV_extract_regesta/blob/main/images/plot_line_bbox.png) ![](https://github.com/SGensicke/PDFtoCSV_extract_regesta/blob/main/images/plot_line_bbox_page_regions.png)

### Resulting table
![](https://github.com/SGensicke/PDFtoCSV_extract_regesta/blob/main/images/result_table.png)
