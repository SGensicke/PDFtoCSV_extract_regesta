# PDFtoCSV_extract_regesta
The aim of this Jupyter notebook is to extract the retro-digitised and OCRed regesta, for example from the volumes of the Göttinger Papsturkundenwerk, into tabular form and to enable their digital processing as part of the Academy project [Die Formierung Europas durch Überwindung der Spaltung im 12. Jahrhundert](https://formierung-europas.badw.de/).

The script relies on the standardised structure of a printed book page to identify individual parts of a Regest. The Python library PyMuPDF is used to extract each line of text. In a first step, the position of blocks and lines on the page can be visualised in order to manually set the limits for the page regions header, footer, page number, Regestennummer, date, and indentation of the first line of a paragraph, taking into account whether the page is even or odd. To see the interactive graphs visualised with plotly (not rendered in github), you can use the [nbviewer](https://nbviewer.org/github/SGensicke/PDFtoCSV_extract_regesta/blob/main/PDFtoCSV_extract_regesta-public.ipynb).

Through page stabilization, all pages are aligned at the intersection of the top and left edges of the type area. This alignment minimizes the deviation in the positional data of individual lines required for categorization.

The program assigns each line to a category based on its positional data and returns the processed text in tabular form. A 'Regestennummer' always marks the beginning of a new entry. The resulting table is saved as a CSV file. Challenges primarily stem from OCR errors, which lead to a chaotic division of the text into spans, lines, and blocks. This often causes misclassification, particularly in distinguishing between the frequently italicized Kopfregesten, archival tradition, and commentary on the one hand, and the regular text of the edition and its footnotes on the other, requiring manual correction.

The code can be adapted to process regesta where, for example, the date is centered below the number or where the number is on the left and the date on the right of the same line. The clearer the visual structure of the text, the better the results.

This tool was developed with the help of ChatGPT.

### Example page, plot of line midpoints
![](https://github.com/SGensicke/PDFtoCSV_extract_regesta/blob/main/images/example_page_PUU_Frankreich_I.png "example page") ![](https://github.com/SGensicke/PDFtoCSV_extract_regesta/blob/main/images/plot_line_midpoints_of_50_left_pages.png)

### Plotted lines of the example page, manually defined areas of interest and classified text parts
![](https://github.com/SGensicke/PDFtoCSV_extract_regesta/blob/main/images/plot_line_bbox.png) ![](https://github.com/SGensicke/PDFtoCSV_extract_regesta/blob/main/images/plot_line_bbox_page_regions.png)

### Resulting table
![](https://github.com/SGensicke/PDFtoCSV_extract_regesta/blob/main/images/result_table.png)
