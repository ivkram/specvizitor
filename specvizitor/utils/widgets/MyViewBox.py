import pyqtgraph as pg


class MyViewBox(pg.ViewBox):
    def updateViewLists(self):
        try:
            self.window()
        except RuntimeError:  ## this view has already been deleted; it will probably be collected shortly.
            return

        nv = list(pg.ViewBox.NamedViews.values())

        if self in nv:
            nv.remove(self)

        if self.menu is not None:
            self.menu.setViewList(nv)

        for ax in [0, 1]:
            link = self.state['linkedViews'][ax]
            if isinstance(link, str):  ## axis has not been linked yet; see if it's possible now
                for v in nv:
                    if link == v.name:
                        self.linkView(ax, v)
