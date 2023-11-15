from qtpy import QtWidgets, QtCore


class Section(QtWidgets.QWidget):
    def __init__(self, title="", animation_duration=100, parent=None):
        super().__init__(parent)

        self.animationDuration = animation_duration

        self.toggleButton = QtWidgets.QToolButton(self)
        self.headerLine = QtWidgets.QFrame(self)
        self.toggleAnimation = QtCore.QParallelAnimationGroup(self)
        self.contentArea = QtWidgets.QScrollArea(self)
        self.mainLayout = QtWidgets.QGridLayout(self)

        self.toggleButton.setStyleSheet("QToolButton {border: none;}")
        self.toggleButton.setToolButtonStyle(QtCore.Qt.ToolButtonTextBesideIcon)
        self.toggleButton.setArrowType(QtCore.Qt.RightArrow)
        self.toggleButton.setText(title)
        self.toggleButton.setCheckable(True)
        self.toggleButton.setChecked(False)

        self.headerLine.setFrameShape(QtWidgets.QFrame.HLine)
        self.headerLine.setFrameShadow(QtWidgets.QFrame.Sunken)
        self.headerLine.setSizePolicy(QtWidgets.QSizePolicy.Expanding, QtWidgets.QSizePolicy.Maximum)

        # self.contentArea.setLayout(wd.QHBoxLayout())
        self.contentArea.setSizePolicy(QtWidgets.QSizePolicy.Expanding, QtWidgets.QSizePolicy.Fixed)

        # start out collapsed
        self.contentArea.setMaximumHeight(0)
        self.contentArea.setMinimumHeight(0)

        # let the entire widget grow and shrink with its content
        self.toggleAnimation.addAnimation(QtCore.QPropertyAnimation(self, b"minimumHeight"))
        self.toggleAnimation.addAnimation(QtCore.QPropertyAnimation(self, b"maximumHeight"))
        self.toggleAnimation.addAnimation(QtCore.QPropertyAnimation(self.contentArea, b"maximumHeight"))

        self.mainLayout.setVerticalSpacing(0)
        self.mainLayout.setContentsMargins(0, 0, 0, 0)

        row = 0
        self.mainLayout.addWidget(self.toggleButton, row, 0, 1, 1, QtCore.Qt.AlignLeft)
        self.mainLayout.addWidget(self.headerLine, row, 2, 1, 1)
        self.mainLayout.addWidget(self.contentArea, row + 1, 0, 1, 3)
        self.setLayout(self.mainLayout)

        self.toggleButton.toggled.connect(self.toggle)

    def set_layout(self, content_layout):
        layout = self.contentArea.layout()
        del layout
        self.contentArea.setLayout(content_layout)
        collapsed_height = self.sizeHint().height() - self.contentArea.maximumHeight()
        content_height = content_layout.sizeHint().height()
        for i in range(0, self.toggleAnimation.animationCount() - 1):
            section_animation = self.toggleAnimation.animationAt(i)
            section_animation.setDuration(self.animationDuration)
            section_animation.setStartValue(collapsed_height)
            section_animation.setEndValue(collapsed_height + content_height)
        content_animation = self.toggleAnimation.animationAt(self.toggleAnimation.animationCount() - 1)
        content_animation.setDuration(self.animationDuration)
        content_animation.setStartValue(0)
        content_animation.setEndValue(content_height)

    def toggle(self, collapsed):
        if collapsed:
            self.toggleButton.setArrowType(QtCore.Qt.DownArrow)
            self.toggleAnimation.setDirection(QtCore.QAbstractAnimation.Forward)
        else:
            self.toggleButton.setArrowType(QtCore.Qt.RightArrow)
            self.toggleAnimation.setDirection(QtCore.QAbstractAnimation.Backward)
        self.toggleAnimation.start()
