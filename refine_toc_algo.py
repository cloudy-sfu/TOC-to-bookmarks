import numpy as np
import pandas as pd
from dbscan1d import DBSCAN1D
from scipy.stats import mode


def get_rotated_angle(content_table):
    r"""
    :param content_table: returned value of infer.predict_system.TextSystem.__call__
    :return: tan(\theta) where \theta \in (-\pi/2, \pi/2) is the rotated angle
        \theta > 0: right corner higher (left rotated)
        \theta < 0: left corner higher (right rotated)
    """
    tan_alpha_ = (content_table['right_upper_y'] - content_table['left_upper_y']) / (
            content_table['right_upper_x'] - content_table['left_upper_x'])
    tan_alpha_mean_1 = np.nanmean(tan_alpha_)
    tan_alpha_ = np.where(tan_alpha_ * tan_alpha_mean_1 < 0, -1 / tan_alpha_, tan_alpha_)
    tan_alpha_mid_2 = np.nanmedian(tan_alpha_)
    return tan_alpha_mid_2


def full_to_half_digit(full_width_digits):
    """
    Convert UTF-8 (full width) digits U+FF10 ... U+FF19 to ASCII (half width) digits
    0 ... 9
    :param full_width_digits: A string containing full-width digits.
    :return: A string with full-width digits converted to half-width digits.
    """
    translator = str.maketrans(
        {chr(i): chr(i - 0xFF10 + 0x30) for i in range(0xFF10, 0xFF1A)}
    )
    ascii_digits = full_width_digits.translate(translator)
    return ascii_digits


def find_title_box(row, others):
    """
    Find the title box corresponding to a given page number box.
    :param row: page number box
    :param others: candidate title box
    :return: the corresponding title box
    """
    # Define "inner_y" are of the page number box
    inner_y_ub = np.maximum(row['left_upper_y'], row['right_upper_y'])
    inner_y_lb = np.minimum(row['left_lower_y'], row['right_lower_y'])

    # Criteria: to the left of page number box
    western_x = np.minimum(row['left_upper_x'], row['left_lower_x'])
    others_1 = others[
        (others['right_upper_x'] < western_x) & (others['right_lower_x'] < western_x)
    ]

    # Criteria: at least 2 vertex of title box should be "inner_y" of page number box
    others_2 = others_1.loc[sum(
        others[f'{vertex_1}_y'].between(inner_y_ub, inner_y_lb)
        for vertex_1 in ['left_upper', 'left_lower', 'right_upper', 'right_lower']
    ) >= 2, :]

    match others_2.shape[0]:
        case 0:
            return pd.Series(index=others_2.columns)
        case 1:
            return others_2.iloc[0, :]
        case _:  # >= 2
            return pd.Series({
                'page': others_2.iloc[0, :],
                'left_upper_x': others_2['left_upper_x'].min().astype(int),
                'left_upper_y': others_2['left_upper_y'].min().astype(int),
                'right_upper_x': others_2['right_upper_x'].max().astype(int),
                'right_upper_y': others_2['right_upper_y'].min().astype(int),
                'right_lower_x': others_2['right_lower_x'].max().astype(int),
                'right_lower_y': others_2['right_lower_y'].max().astype(int),
                'left_lower_x': others_2['left_lower_x'].min().astype(int),
                'left_lower_y': others_2['left_lower_y'].max().astype(int),
                'text': others_2.sort_values(
                    by=['left_upper_x', 'left_upper_y'],
                    key=lambda x: others_2['left_upper_x'] + others_2['left_upper_y']
                )['text'].astype(str).str.cat(sep=' ')
            })


def get_toc(content_table):
    # Rotate to horizontal 0 degree.
    tan_alpha = get_rotated_angle(content_table)
    for vertex in ['left_upper', 'left_lower', 'right_upper', 'right_lower']:
        content_table[f'{vertex}_x'] = content_table[f'{vertex}_x'] + tan_alpha * content_table[f'{vertex}_y']

    page_numbers_right = mode(content_table['right_upper_x']).mode
    page_numbers_idx_1 = content_table['right_upper_x'] == page_numbers_right
    tol = (content_table.loc[page_numbers_idx_1, 'right_upper_x'] -
           content_table.loc[page_numbers_idx_1, 'left_upper_x']).mean() / 2
    page_numbers_idx_2 = (page_numbers_right - tol < content_table['right_upper_x']) & (
            content_table['right_upper_x'] < page_numbers_right + tol)
    page_numbers = content_table[page_numbers_idx_2]
    titles = page_numbers.apply(
        find_title_box, axis=1, args=(content_table[~page_numbers_idx_2],))
    dbscan = DBSCAN1D(eps=tol, min_samples=2)
    labels = dbscan.fit_predict(titles['left_upper_x'].values)
    labels = np.where(labels == -1, np.nan, labels + 1)
    toc_page = pd.DataFrame({
        'level': labels,
        'title': titles['text'],
        'page_number': page_numbers['text'],
    })
    return toc_page


if __name__ == '__main__':
    content_table_ = pd.read_pickle("tests/content_tables.pkl")
    content_table_['text'] = content_table_['text'].map(full_to_half_digit)
    toc_ = get_toc(content_table_)
    toc_.to_pickle("tests/toc.pkl")
    print(toc_)
