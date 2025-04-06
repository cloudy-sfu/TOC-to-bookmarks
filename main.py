import logging
import sys
import traceback
from argparse import Namespace

import pandas as pd
import yaml
from PyQt5.QtWidgets import QApplication, QDialog
from tqdm import tqdm

from ask_ocr import OCRDialog
from infer.predict_system import TextSystem
from preview import PDFViewer, get_file
from refine_toc_algo import full_to_half_digit, get_toc
from refine_toc_gui import TocRefinement
from write_toc import export

# %% Initialization.
app = QApplication([])
logging.basicConfig(
    datefmt="%Y-%m-%d %H:%M:%S",
    format="%(levelname).1s %(asctime)s %(message)s",
    level=logging.INFO
)

def handle_exception(exc_type, exc_value, exc_traceback):
    msg = f"{exc_type.__name__}: {exc_value}\nTraceback:\n{''.join(
        traceback.format_tb(exc_traceback))}"
    logging.error(msg)

sys.excepthook = handle_exception

# %% Ask OCR.
ocr_dialog = OCRDialog()
ocr_enabled = ocr_dialog.exec_() == QDialog.Accepted

# %% Get file path.
logging.info("[1/6] Interactive: open the book.")
fp = get_file()
assert fp, "PDF file doesn't exist."

# %% Get range of TOC and start of main content.
logging.info("[2/6] Interactive: understand the book's structure.")

viewer = PDFViewer(fp)
if ocr_enabled:
    viewer.set_text_name("Browse to the first page of \"Table of Content\".")
    viewer.show()
    viewer.render_page(1)
    app.exec_()
    toc_first_page = viewer.current_page

    viewer.set_text_name("Browse to the last page of \"Table of Content\".")
    viewer.show()
    viewer.render_page(toc_first_page)
    app.exec_()
    toc_last_page = viewer.current_page
    logging.info(f"TOC is from physical page {toc_first_page} to {toc_last_page}.")
    assert 1 <= toc_first_page <= toc_last_page, "Page range of TOC is invalid."

viewer.set_text_name("Browse to first page of main content (logical page 1).")
viewer.show()
if ocr_enabled:
    viewer.render_page(toc_last_page)
else:
    viewer.render_page(1)
app.exec_()
main_first_page = viewer.current_page
logging.info(f"Main content is from physical page {main_first_page}.")

n = viewer.document.page_count
if ocr_enabled:
    assert toc_last_page < main_first_page, "Main content should be after TOC."
    assert main_first_page <= n, "Start page of main content is invalid."
else:
    assert 1 <= main_first_page <= n, "Start page of main content is invalid."

if ocr_enabled:
    # Initialize OCR model.
    logging.info("[3/6] Initialize OCR model.")
    with open("configs/arguments.yaml", "r", encoding="utf-8") as f:
        yaml_config = yaml.safe_load(f)
    ns = Namespace(**yaml_config)
    text_system = TextSystem(ns)

    # Run OCR.
    logging.info("[4/6] Generate TOC.")
    toc = []
    for i in tqdm(range(toc_first_page, toc_last_page + 1), desc="Pages"):
        page = viewer.to_cv2_array(i)
        content_table = text_system(page)
        content_table.insert(loc=0, column="page", value=i)
        content_table['text'] = content_table['text'].map(full_to_half_digit)

        # Organize TOC structure.
        toc_ = get_toc(content_table)
        toc.append(toc_)

    viewer.document.close()
    toc = pd.concat(toc, ignore_index=True, axis=0)
else:
    viewer.document.close()

# %% Refine TOC.
logging.info("[5/6] Interactive: refine TOC.")
toc_refinement = TocRefinement()
if ocr_enabled:
    toc_refinement.set_table(toc)
toc_refinement.show()
app.exec_()
toc = toc_refinement.get_table()

# %% Insert bookmarks.
logging.info("[6/6] Insert bookmarks to the book.")
toc['page_number'] = toc['page_number'] + main_first_page - 1
new_fp = export(fp, toc)
logging.info(f"The modified book is saved at {new_fp}")
