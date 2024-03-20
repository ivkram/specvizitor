import pyqtgraph as pg
from pgcolorbar.colorlegend import ColorLegendItem
import numpy as np

from .MyViewBox import MyViewBox


class ColorBar(ColorLegendItem):
    def __init__(self, *args, **kwargs):
        pg.ViewBox = MyViewBox
        super().__init__(*args, **kwargs)

    def _calcHistogramRange(self, imgArr, step='auto', targetImageSize=200):
        if imgArr is None or imgArr.size == 0 or np.all(~np.isfinite(imgArr)):
            return None, None

        mn, mx = self.getLevels()

        return mn, mx
