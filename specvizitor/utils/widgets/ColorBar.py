import numpy as np

from pgcolorbar.colorlegend import ColorLegendItem


class ColorBar(ColorLegendItem):
    def _calcHistogramRange(self, imgArr, step='auto', targetImageSize=200):
        if imgArr is None or imgArr.size == 0 or np.all(~np.isfinite(imgArr)):
            return None, None

        mn, mx = self.getLevels()

        return mn, mx
