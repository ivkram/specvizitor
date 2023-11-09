from astropy.visualization import ZScaleInterval
import numpy as np

from pgcolorbar.colorlegend import ColorLegendItem


class ColorBar(ColorLegendItem):
    @classmethod
    def _calcHistogramRange(cls, imgArr, step='auto', targetImageSize=200):
        if imgArr is None or imgArr.size == 0 or np.all(~np.isfinite(imgArr)):
            return None, None

        mn, mx = ZScaleInterval().get_limits(imgArr)

        return mn, mx
