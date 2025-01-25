import os

import fitz


def export(fp, toc):
    bare_fp, ext = os.path.splitext(fp)
    new_fp = bare_fp + "_outlined.pdf"
    with fitz.open(fp) as doc:
        bookmarks = doc.get_toc(simple=False)
        for i, row in toc.iterrows():
            bookmarks.append([row['level'], row['title'], row['page_number'], 0])
        doc.set_toc(bookmarks)
        doc.save(garbage=1, filename=new_fp)
    return new_fp
