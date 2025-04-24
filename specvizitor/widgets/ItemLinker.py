import abc
import logging

from .ViewerElement import ViewerElement, SliderItem
from .Image2D import Image2D


__all__ = [
    "ItemLinker",
    "XAxisLinker",
    "YAxisLinker",
    "SliderLinker",
    "ColorBarLinker"
]

logger = logging.getLogger(__name__)


class ItemLinker(abc.ABC):
    allowed_widget_type: type[ViewerElement] = ViewerElement

    def _validate(self, *args):
        if any(not isinstance(a, self.allowed_widget_type) for a in args):
            return False
        return True

    @abc.abstractmethod
    def _get_link_from_cfg(self, w1: ViewerElement) -> str:
        pass

    @abc.abstractmethod
    def _link(self, w1: ViewerElement, w2: ViewerElement):
        pass

    def link(self, w1: ViewerElement, w2: ViewerElement, links: dict):
        if not self._validate(w1, w2):
            return
        if not self._get_link_from_cfg(w1) == w2.title:
            return

        if w1.title == w2.title:
            logger.error(f"Cannot link a widget to itself (widget: {w1.title}, linker: {type(self).__name__})")
            return

        self._link(w1, w2)
        links[w1.title] = w2.title
        logger.debug(f"Widgets linked (link: {w1.title} --> {w2.title}, linker: {type(self).__name__})")

    @abc.abstractmethod
    def _unlink(self, w1: ViewerElement, w2: ViewerElement):
        pass

    def unlink(self, w1: ViewerElement, w2: ViewerElement, links: dict):
        if not links.get(w1.title) == w2.title:
            return

        self._unlink(w1, w2)
        links.pop(w1.title)
        logger.debug(f"Widgets unlinked (link: {w1.title} --> {w2.title}, linker: {type(self).__name__})")


class XAxisLinker(ItemLinker):
    def _get_link_from_cfg(self, w1: ViewerElement) -> str:
        return w1.cfg.x_axis.link_to

    def _link(self, w1: ViewerElement, w2: ViewerElement):
        w1.container.setXLink(w2.title)

    def _unlink(self, w1: ViewerElement, w2: ViewerElement):
        w1.container.setXLink(None)


class YAxisLinker(ItemLinker):
    def _get_link_from_cfg(self, w1: ViewerElement) -> str:
        return w1.cfg.y_axis.link_to

    def _link(self, w1: ViewerElement, w2: ViewerElement):
        w1.container.setYLink(w2.title)

    def _unlink(self, w1: ViewerElement, w2: ViewerElement):
        w1.container.setYLink(None)


class SliderLinker(ItemLinker):
    def __init__(self, slider: SliderItem):
        super().__init__()
        self._slider: SliderItem = slider

    def _get_link_from_cfg(self, w1: ViewerElement) -> str:
        return w1.sliders[self._slider].link_to

    def _link(self, w1: ViewerElement, w2: ViewerElement):
        slider1, slider2 = w1.sliders[self._slider], w2.sliders[self._slider]
        slider1.value_changed[float].connect(slider2.set_value)
        slider2.value_changed[float].connect(slider1.set_value)

    def _unlink(self, w1: ViewerElement, w2: ViewerElement):
        slider1, slider2 = w1.sliders[self._slider], w2.sliders[self._slider]
        slider1.value_changed[float].disconnect(slider2.set_value)
        slider2.value_changed[float].disconnect(slider1.set_value)


class ColorBarLinker(ItemLinker):
    allowed_widget_type = Image2D

    def _get_link_from_cfg(self, w1: Image2D) -> str:
        return w1.cfg.color_bar.link_to

    def _link(self, w1: Image2D, w2: Image2D):
        w1.cbar.sigLevelsChanged[tuple].connect(w2.set_levels)
        w2.cbar.sigLevelsChanged[tuple].connect(w1.set_levels)

    def _unlink(self, w1: Image2D, w2: Image2D):
        w1.cbar.sigLevelsChanged[tuple].disconnect(w2.set_levels)
        w2.cbar.sigLevelsChanged[tuple].disconnect(w1.set_levels)
