# PDFtoCSV_extract_regesta
The aim of this the Jupyter notebook is to extract the retro-digitised regesta, for example from the volumes of the Göttinger Papsturkundenwerk, into tabular form and to enable their digital processing as part of the Academy project [Die Formierung Europas durch Überwindung der Spaltung im 12. Jahrhundert](https://formierung-europas.uni-koeln.de/).

The script relies on the standardised structure of a printed book page to identify individual parts of a Regest. The Python library PyMuPDF is used to extract each line of text. In a first step, the position of blocks and lines on the page can be visualised in order to manually set the limits for the page regions header, footer, page number, Regestennummer, and date, taking into account whether the page is even or odd.

In the next step, the program assigns each line to a category based on its positional data and outputs the processed text in tabular form. Regestennummer always marks the start of a new entry. The resulting table is saved as a CSV file.
Difficulties arise mainly from OCR errors and the resulting rather chaotic division of the text into spans, lines and blocks, so that errors occur particularly in distinguishing between the often italicised Kopfregesten, archival tradition and comments on the one hand, and the regular text of the edition on the other, which until now have to be corrected manually.

This tool was developed using ChatGPT.

### Example page, plot of line midpoints
![](https://github.com/SGensicke/PDFtoCSV_extract_regesta/blob/main/images/example_page_PUU_Frankreich_I.png "example page") ![](https://github.com/SGensicke/PDFtoCSV_extract_regesta/blob/main/images/plot_line_midpoints_of_50_left_pages.png)

### Plotted lines of the example page, manually defined areas of interest and classified text parts
![](https://github.com/SGensicke/PDFtoCSV_extract_regesta/blob/main/images/plot_line_bbox.png) ![](https://github.com/SGensicke/PDFtoCSV_extract_regesta/blob/main/images/plot_line_bbox_page_regions.png)

### Resulting table
![](https://github.com/SGensicke/PDFtoCSV_extract_regesta/blob/main/images/result_table.png)
