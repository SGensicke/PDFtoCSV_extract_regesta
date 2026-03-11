import fitz  # PyMuPDF
import numpy as np
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from plotly.subplots import make_subplots
from collections import defaultdict


class PDFProcessor:
    def __init__(self, parameter):
        self.doc = fitz.open(parameter['path'])
        # compute difference between PDF and printed page numbers
        self.page_diff = parameter['pdf_pages'][0] - parameter['first_print_page']
        self.pdf_page_range = range(parameter['pdf_pages'][0] - 1, min(parameter['pdf_pages'][1], len(self.doc)))

    def load_pages(self):
        pages = {}
        for pdf_page in self.pdf_page_range:
            page = self.doc.load_page(pdf_page)
            print_page = pdf_page - self.page_diff + 1
            pages[print_page] = page

        return pages
    
    def close(self):
        self.doc.close()

# --- Preprocessing ---
class PageCleaner:
    @staticmethod
    def remove_image_blocks(content):
        content["blocks"] = [b for b in content.get("blocks", []) if b.get("type") == 0]
        return content

    @staticmethod
    def change_rotation(bbox, matrix):
        points = [fitz.Point(*p) * matrix for p in [
            (bbox[0], bbox[1]),
            (bbox[2], bbox[1]),
            (bbox[2], bbox[3]),
            (bbox[0], bbox[3])
        ]]
        xs, ys = zip(*points)
        return min(xs), min(ys), max(xs), max(ys)

    @staticmethod
    def reduce_scattering(content):
        blocks = content.get("blocks", [])
        if not blocks:
            return content

        min_x = min(block['bbox'][0] for block in blocks)
        min_y = min(block['bbox'][1] for block in blocks)

        second_min_x = min((b['bbox'][0] for b in blocks if b['bbox'][0] != min_x), default=min_x)
        second_min_y = min((b['bbox'][1] for b in blocks if b['bbox'][1] != min_y), default=min_y)

        for block in blocks:
            block['bbox'] = PageCleaner._shift_bbox(block['bbox'], second_min_x, second_min_y)
            for line in block.get('lines', []):
                line['bbox'] = PageCleaner._shift_bbox(line['bbox'], second_min_x, second_min_y)
                for span in line.get('spans', []):
                    span['bbox'] = PageCleaner._shift_bbox(span['bbox'], second_min_x, second_min_y)
        return content

    @staticmethod
    def _shift_bbox(bbox, dx, dy):
        x0, y0, x1, y1 = bbox
        return x0 - dx, y0 - dy, x1 - dx, y1 - dy
    
    @staticmethod
    def reduce_scattering2(content):

        blocks = content.get("blocks", [])
        if not blocks:
            return content

        xs = []
        ys = []

        for block in blocks:
            xs.append(block['bbox'][0])
            ys.append(block['bbox'][1])

            for line in block.get("lines", []):
                xs.append(line['bbox'][0])
                ys.append(line['bbox'][1])

                for span in line.get("spans", []):
                    xs.append(span['bbox'][0])
                    ys.append(span['bbox'][1])

        dx = np.percentile(xs, 15)
        dy = np.percentile(ys, 15)

        for block in blocks:
            block['bbox'] = PageCleaner._shift_bbox(block['bbox'], dx, dy)

            for line in block.get("lines", []):
                line['bbox'] = PageCleaner._shift_bbox(line['bbox'], dx, dy)

                for span in line.get("spans", []):
                    span['bbox'] = PageCleaner._shift_bbox(span['bbox'], dx, dy)

        return content

    def merge_lines(block, gap=5.0):

    #        def merge_spans(line, gap=5.0):

    #            merged_spans = []
    #            current_span = None

    #            for span in line["spans"]:
    #                if current_span is None:
    #                    current_span = span.copy()
    #                else:
    #                    same_line = abs(span["bbox"][1] - current_span["bbox"][1]) < 1.0
    #                    same_font = span["font"] == current_span["font"]
    #                    close_x = (span["bbox"][0] - current_span["bbox"][2]) <= gap

    #                    if same_line and same_font and close_x:
    #                        # Merge Text
    #                        current_span["text"] += span["text"]
    #                        # Merge bbox (neue Breite)
    #                        current_span["bbox"] = (
    #                            current_span["bbox"][0],  # x0 bleibt
    #                            current_span["bbox"][1],  # y0 bleibt
    #                           span["bbox"][2],          # x1 vom neuen Span
    #                            max(current_span["bbox"][3], span["bbox"][3])  # y1 max
    #                        )
    #                    else:
    #                        merged_spans.append(current_span)
    #                        current_span = span.copy()

    #            if current_span:
    #                merged_spans.append(current_span)
    #            line["spans"] = merged_spans
    #            return line
            

            merged_lines = []
            current_line = None    
            
            for line in block["lines"]:
                if current_line == None:
                    current_line = line.copy()
                else:
                    same_y = abs(line["bbox"][1] - current_line["bbox"][1]) < 1.0
                    close_x = (line["bbox"][0] - current_line["bbox"][2] <= gap)

                    if same_y and close_x:
                        current_line["spans"].extend(line["spans"])
                        current_line["bbox"] = (
                            current_line["bbox"][0],
                            current_line["bbox"][1],
                            line["bbox"][2],
                            max(current_line["bbox"][3], line["bbox"][3])
                        )
                    else:
                        merged_lines.append(current_line)
                        current_line = line.copy()
            if current_line:
                merged_lines.append(current_line)
            
            block["lines"] = merged_lines
            return block

# --- Prepare lines for flassification ---
class LineProcessor:
    @staticmethod
    def process(content, print_page, pdf_page, parameter):
        data = []
        for block in content.get('blocks', []):
            block_type = 'a-block' if print_page % 2 == 0 else 'b-block'
            data.append((*block['bbox'], None, None, block_type, pdf_page, print_page))
            for line in block.get("lines", []):
                # add scip empty lines?
                # ignore lines containing fonts used in Watermarks (maybe move to span level or collect irgnored spans?)
                if 'ignore_fonts' in parameter:
                    if any(span['font'] in parameter['ignore_fonts'] for span in line.get('spans', [])):
                        continue
                line_bbox, line_text, is_italic = LineProcessor._process_line(line, print_page, parameter)
                line_type = 'a-line' if print_page % 2 == 0 else 'b-line'
                x_center = (line_bbox[0] + line_bbox[2]) / 2
                y_center = (line_bbox[1] + line_bbox[3]) / 2
                data.append((*line_bbox, x_center, y_center, line_type, pdf_page, print_page, line_text, is_italic))
        return data

    @staticmethod
    def _process_line(line, print_page, parameter):
        i_count = r_count = 0
        line_text = ''
        line_bbox = line['bbox']

        for span in line.get('spans', []):
            # count italic and non italic spans of each line 
            if ('Italic' or 'italic') in span['font']:
                i_count += 1
            else:
                r_count += 1

            # shorten spans and lines that extend beyond the text field due to an error in ocr
            if parameter['compensate_ocr_error']:
                ocr_limit = parameter['ocr_error']['a-page'] if print_page % 2 == 0 else parameter['ocr_error']['b-page']

                if span['bbox'][2] > ocr_limit:
                    sx0, sy0, _, sy1 = span['bbox']
                    span['bbox'] = (sx0, sy0, sx0, sy1) # shorten span (is this even necessery?)

                    lx0, ly0, _, ly1 = line_bbox
                    line_bbox = (lx0, ly0, sx0, ly1) # shorten line
            
            # combine span texts of each line
            line_text += span['text']
        return line_bbox, line_text, i_count > r_count


# --- Rule-based classification of individual lines ---
class ParagraphClassifier:
    def __init__(self, df, parameter_a, parameter_b):
        self.df = df
        self.parameter_a = parameter_a
        self.parameter_b = parameter_b

        self.classified_text = []
        self.previous_category = None
        self.previous_text = []
        self.i_count = 0
        self.r_count = 0
        self.previous_line_bbox = (0, 0, 0, 0)
        self.pagerange_print = []
        self.pagerange_pdf = []

    # select parameter according to print page
    def get_parameter(self, print_page: int) -> dict:
        return self.parameter_a if (print_page % 2) == 0 else self.parameter_b

    # decide wether a new paragraph begins
    def new_paragraph(self, category: str, x0: float, parameter: dict) -> bool:
        return (
            category != self.previous_category
            or parameter['indentation_start'] < x0 < parameter['indentation_end']
        )

    # append text and classification to classified_text
    def save_paragraph(self):
        if self.previous_category:
            # it may depend on the edition which text is in italics, so it may be necessary to reverse the '>'.
            if self.previous_category == 'other' and self.i_count > self.r_count:
                paragraph_type = 'e-Regestentext'
            else:
                paragraph_type = self.previous_category

            self.classified_text.append({
                'type': paragraph_type,
                'value': ' '.join(self.previous_text)
            })

            self.classified_text.append({
                'type': 'print_page',
                'value': self.pagerange_print
            })
            self.classified_text.append({
                'type': 'pdf_page',
                'value': self.pagerange_pdf
            })

    # line classification
    def classify_line(self, row, previous_line_bbox, parameter):
        width = row['x1'] - row['x0']
        
        if row['y_center'] < parameter['header_border'] and parameter['left_pagenumber_border'] < row['x_center'] < parameter['right_pagenumber_border']:
            return 'header'
        elif row['x_center'] < parameter['left_pagenumber_border'] and (row['y_center'] < parameter['header_border'] or row['y_center'] > parameter['footer_border']):    # left standing page number
            return 'a-page'
        elif row['x_center'] > parameter['right_pagenumber_border'] and (row['y_center'] < parameter['header_border'] or row['y_center'] > parameter['footer_border']):   # right standing page number
            return 'b-page'
        elif row['y_center'] > parameter['footer_border']:
            return 'footer'
        elif width < parameter['number_width'] and parameter['mid_strip_start'] < row['x_center'] < parameter['mid_strip_end']:
            return 'c-Regestennummer'
        elif ((row['x0'] - previous_line_bbox[2] > 40) or (abs(previous_line_bbox[1] - row['y0']) > 10)) and (parameter['date_strip_start'] < row['x_center'] < parameter['date_strip_end']):
            return 'date'
        else:
            return 'other'
        
    # paragraph classification
    def classify_pragraph(self):
        for row in self.df.to_dict('records'):
            parameter = self.get_parameter(row['print_page'])
            category = self.classify_line(row, self.previous_line_bbox, parameter)

            if row['italic']:
                self.i_count += 1
            else:
                self.r_count += 1

            self.pagerange_print.append(row['print_page'])
            self.pagerange_pdf.append(row['pdf_page'])

            if category:
                if self.new_paragraph(category, row['x0'], parameter):
                    self.save_paragraph()

                    self.previous_category = category
                    self.previous_text = [row['line']]
                    self.i_count = 0
                    self.r_count = 0
                    self.pagerange_print = []
                    self.pagerange_pdf = []
                else:
                    self.previous_text.append(row['line'])

                self.previous_line_bbox = (row['x0'], row['y0'], row['x1'], row['y1'])

        # Save last paragraph
        self.save_paragraph()

        return self.classified_text
    

class Regesta:
    def __init__(self):
        self.content_raw = {}
        self.content_processed = {}
        self.pages = {}
        self.av_print_page_no = ()
        self.processed_df = pd.DataFrame()
        self.classified_texts = []
        self.regesta_data = []
        self.pre_export_df = pd.DataFrame()
        self.export_df = pd.DataFrame()

    def open(self, parameter):
        processor = PDFProcessor(parameter)
        print("Load pages...")
        self.pages = processor.load_pages()
        self.av_print_page_no = (min(self.pages), max(self.pages))
        print("Get texts...")
        for print_page, page in self.pages.items():
            self.content_raw[print_page] = page.get_text("dict")

    def collect_fonts(self):
        fonts_found = set()
        for page_content in self.content_raw.values():
            for block in page_content.get("blocks", []):
                for line in block.get("lines", []):
                    for span in line.get("spans", []):
                        fonts_found.add(span['font'])
        return fonts_found
    
    def check_font(self, font):
        for key, page in self.content_processed.items():
            for block in page['blocks']:
                for line in block['lines']:
                    for span in line['spans']:
                        if span['font'] == font:
                            print(key, span['text'])
    
    def print_page_spans(self, page):
        for block in self.content_processed[page]['blocks']:
                for line in block['lines']:
#                    print("Line:")
                    for span in line['spans']:
                        print(" ", span['size'], span['flags'], span['font'], span['bbox'], span['text'])

    def print_page_lines(self, page):
        for block in self.content_processed[page]['blocks']:
                for line in block['lines']:
                    line_info = f"Spans: {len(line['spans'])}, {line['bbox']}"
                    line_text = ""
                    for span in line['spans']:
                        line_text += span['text']
                    print(line_info, line_text)

    def preprocess_text(self, parameter):
        print("Collecting fonts...")
        fonts_on_pages = self.collect_fonts()
        print("Fonts found in document:")
        for font in fonts_on_pages:
              print(" ", font)
        all_data = []
        print("Preprocessing pages...")
        for print_page, page in self.pages.items():
            content = page.get_text("dict")
            rotation = page.rotation_matrix if page.rotation else None

            content = PageCleaner.remove_image_blocks(content)

            if rotation:
                for block in content.get("blocks", []):
                    block['bbox'] = PageCleaner.change_rotation(block['bbox'], rotation)
                    for line in block.get("lines", []):
                        line['bbox'] = PageCleaner.change_rotation(line['bbox'], rotation)
            PageCleaner.reduce_scattering(content)

            if parameter['merge_lines']['active']==True:
                for block in content.get("blocks", []):
                        block = PageCleaner.merge_lines(block, parameter['merge_lines']['gap'])
            
            page_data = LineProcessor.process(content, print_page, page.number + 1, parameter)
            all_data.extend(page_data)

            self.content_processed[print_page] = content

        self.processed_df = pd.DataFrame(all_data, columns=[
            'x0', 'y0', 'x1', 'y1', 'x_center', 'y_center',
            'type', 'pdf_page', 'print_page', 'line', 'italic'
        ])
        print("Done!")

    def classify_text(self, parameter_a, parameter_b):
        df = self.processed_df[self.processed_df['type'].isin(['a-line', 'b-line'])].copy()
        classifier = ParagraphClassifier(df, parameter_a, parameter_b)
        self.classified_texts = classifier.classify_pragraph()
        self._build_regesta(self.classified_texts)


    def _build_regesta(self, classified_texts):

        regesta = []
        current_regest = {}
        counter = defaultdict(int)

        for text in classified_texts:
            if text['type'] == "c-Regestennummer":
                if current_regest:
                    regesta.append(current_regest)
                current_regest = {"c-Regestennummer": text['value']}
                counter = defaultdict(int)
            else:
                key = text['type']
                counter[key] += 1
                if counter[key] == 1:
                    new_key = key
                else:
                    new_key = f"{key}_{counter[key]:03d}"
                current_regest[new_key] = text['value']
        if current_regest:
            regesta.append(current_regest)
        self.regesta_data = regesta
    
    def prepare_export(self):
        df = pd.DataFrame(self.regesta_data)
        self.pre_export_df = df.sort_index(axis=1)
    
    def postprocessing(self):
        df = self.pre_export_df
        print_columns = [col for col in df if 'print' in col]
        df['Druckseiten'] = df[print_columns].apply(lambda row: sorted([item for sublist in row if isinstance(sublist, list) for item in sublist if not pd.isna(item)]), axis=1)
        df.drop(columns=print_columns, inplace=True)
        df['Druckseiten'] = df['Druckseiten'].apply(lambda x: [f'{min(x)}-{max(x)}'] if len(x) > 1 and min(x) != max(x) else [min(x)] if len(x) > 0 else [])
        df['Druckseiten'] = df['Druckseiten'].apply(lambda x: ', '.join(map(str, x)) if isinstance(x, list) else x)

        pdf_columns = [col for col in df if 'pdf' in col]
        df['PDFSeiten'] = df[pdf_columns].apply(lambda row: sorted([item for sublist in row if isinstance(sublist, list) for item in sublist if not pd.isna(item)]), axis=1)
        df.drop(columns=pdf_columns, inplace=True)
        df['PDFSeiten'] = df['PDFSeiten'].apply(lambda x: [f'{min(x)}-{max(x)}'] if len(x) > 1 and min(x) != max(x) else [min(x)] if len(x) > 0 else [])
        df['PDFSeiten'] = df['PDFSeiten'].apply(lambda x: ', '.join(map(str, x)) if isinstance(x, list) else x)


        seite_columns = [col for col in df if 'page' in col]
        df['Seitenbereich'] = df[seite_columns].astype(str).apply(lambda row: sorted(row.values), axis=1)
        df.drop(columns=seite_columns, inplace=True)
        df['Seitenbereich'] = df['Seitenbereich'].apply(lambda x: [i for i in x if i != 'nan'])

        header_columns = [col for col in df if 'header' in col]
        df['Headerbereich'] = df[header_columns].astype(str).apply(lambda row: sorted(row.values), axis=1)
        df.drop(columns=header_columns, inplace=True)
        df['Headerbereich'] = df['Headerbereich'].apply(lambda x: [i for i in x if i != 'nan'])
        
        self.export_df = df
        return df

# --- Plot the coordinates of block or line bbox as rectangles ---
def plot_pagelines(page, df):
    rect_df = df[df['print_page'] == page]

    # create the figure
    fig = go.Figure()

    # ad block and line bbox as rectangles
    for _, row in rect_df.iterrows():
        line_color = "blue" if (row['type'] == 'a-block') or (row['type'] == 'b-block') else "red"
        line_width = 4 if (row['type'] == 'a-block') or (row['type'] == 'b-block') else 2
        fig.add_shape(
            type="rect",
            x0=row['x0'], y0=row['y0'],
            x1=row['x1'], y1=row['y1'],
            line=dict(color = line_color, width = line_width)
        )

    # set limits for the axes
    fig.update_layout(
        xaxis=dict(range=[-100, 500]),
        yaxis=dict(range=[800, -100]),
        width=500,
        height=700
    )

    fig.show()

# --- Plot the coordinates of the line corner points
#       The hover labels show the text of the corresponding line
def plot_coordinates(df, plottype, save=False):
    if type(plottype) == str:
        vdf = df[df['type']==plottype]
    elif type(plottype) == int:
        vdf = df[df['print_page']==plottype]
    elif type(plottype) == tuple:
        vdf = df[(plottype[0]<df['print_page'])&(df['print_page']<plottype[1])]
    elif type(plottype) == dict:
        vdf = df[(plottype['pagerange'][0]<df['print_page'])&(df['print_page']<plottype['pagerange'][1])]
        vdf = vdf[vdf['type']==plottype['bbox']]
    
    fig = make_subplots(
        rows=1,
        cols=2,
#        cols=3,
        subplot_titles=(
            'upper left coordinates: (x0, y0)', 
            'midpoints: ((x0+x1)/2, (y0+y1)/2)', 
#            'lower right coordinates: (x1, y1)'
    ))

    # upper left coordinates
    fig.add_trace(
        go.Scatter(x=vdf['x0'], y=vdf['y0'], mode='markers', marker=dict(color='red'),
                   text= ('S. ' + vdf['print_page'].astype(str) + ':   ' + vdf['line'].astype(str)).tolist(), hoverinfo='text', name='(x0, y0)',
                    hovertemplate=
                    "%{text}<br>" +
                    "x: %{x}<br>" +
                    "y: %{y}<extra></extra>"),
        row=1, col=1
    )

    # midpoints
    fig.add_trace(
        go.Scatter(x=vdf['x_center'], y=vdf['y_center'], mode='markers', marker=dict(color='green'),
                   text=('S. ' + vdf['print_page'].astype(str) + ':   ' + vdf['line'].astype(str)).tolist(), hoverinfo='text', name='((x0+x1)/2, (y0+y1)/2)',
                    hovertemplate=
                    "%{text}<br>" +
                    "x: %{x}<br>" +
                    "y: %{y}<extra></extra>"),
        row=1, col=2
    )

    # lower right coordinates
#    fig.add_trace(
#        go.Scatter(x=vdf['x1'], y=vdf['y1'], mode='markers', marker=dict(color='blue'),
#                   text=('S. ' + vdf['print_page'].astype(str) + ':   ' + vdf['line'].astype(str)).tolist(), hoverinfo='text', name='(x1, y1)',
#                    hovertemplate=
#                    "%{text}<br>" +
#                    "x: %{x}<br>" +
#                    "y: %{y}<extra></extra>"),
#        row=1, col=3
#    )

    # invert y-axis to reproduce page layout
    fig.update_yaxes(autorange='reversed', row=1, col=1)
    fig.update_yaxes(autorange='reversed', row=1, col=2)
#    fig.update_yaxes(autorange='reversed', row=1, col=3)

    fig.update_layout(height=600, width=1000, title_text="Coordinates Plot", showlegend=False)
    fig.show()

    if save:
        fig.write_html(save)
        print(save)