from pyqtgraph.Qt import QtCore, QtGui
import pyqtgraph.opengl as gl
from pyqtgraph.opengl import MeshData
import numpy as np
import threading


class GPGLViewWidget(gl.GLViewWidget, QtCore.QObject):
    exit_signal = QtCore.pyqtSignal()
    show_signal = QtCore.pyqtSignal()
    clear_signal = QtCore.pyqtSignal()
    add_item_delegate_signal = QtCore.pyqtSignal(object, object)
    remove_item_delegate_signal = QtCore.pyqtSignal(object)
    method_delegate_signal = QtCore.pyqtSignal(object, object)

    def __init__(self, parent=None):
        super(GPGLViewWidget, self).__init__(parent=parent)
        self.execute_event_lock = threading.Lock()
        self.execute_event = threading.Event()
        self.execute_result = None
        self.real_close = False

        self.show_signal.connect(self.show_slot)
        self.clear_signal.connect(self.clear_slot)
        self.add_item_delegate_signal.connect(self.add_item_delegate_slot)
        self.remove_item_delegate_signal.connect(self.remove_item_delegate_slot)
        self.method_delegate_signal.connect(self.method_delegate_slot)
        self.exit_signal.connect(self.exit_slot)

    def closeEvent(self, event):
        if not self.real_close:
            event.ignore()
            self.hide()
        else:
            super(GPGLViewWidget, self).closeEvent(event)

    @QtCore.pyqtSlot()
    def show_slot(self):
        self.show()

    @QtCore.pyqtSlot()
    def clear_slot(self):
        self.items = []
        self.update()

    @QtCore.pyqtSlot(object, object)
    def add_item_delegate_slot(self, func, params):
        item = func(**params)
        self.addItem(item)
        self.execute_result = item
        self.execute_event.set()

    @QtCore.pyqtSlot(object)
    def remove_item_delegate_slot(self, item):
        self.removeItem(item)
        self.execute_event.set()

    @QtCore.pyqtSlot(object, object)
    def method_delegate_slot(self, name, params):
        method = getattr(self, name)
        self.execute_result = method(**params)
        self.execute_event.set()

    @QtCore.pyqtSlot()
    def exit_slot(self):
        print('kill')
        self.real_close = True
        self.close()


class GPVisualizer(threading.Thread):
    app = None

    def __init__(self):
        super(GPVisualizer, self).__init__()
        self.running = threading.Event()
        self.start()
        self.running.wait()

    def run(self):
        if GPVisualizer.app is None:
            GPVisualizer.app = QtGui.QApplication([])

        self.widget = GPGLViewWidget()
        self.widget.opts['distance'] = 20
        self.widget.setWindowTitle('default')

        self.running.set()
        self.app.exec()
        self.running.clear()

    def show(self):
        self.running.wait()
        self.widget.show_signal.emit()

    def clear(self):
        self.running.wait()
        self.widget.clear_signal.emit()

    def add_item_delegate(self, func, params):
        self.running.wait()
        self.widget.execute_event_lock.acquire()
        self.widget.execute_event.clear()

        self.widget.add_item_delegate_signal.emit(func, params)
        self.widget.execute_event.wait()

        result = self.widget.execute_result
        self.widget.execute_result = None
        self.widget.execute_event_lock.release()
        return result

    def method_delegate(self, name, params=None):
        self.running.wait()
        self.widget.execute_event_lock.acquire()
        self.widget.execute_event.clear()

        if params is None:
            params = dict()
        self.widget.method_delegate_signal.emit(name, params)
        self.widget.execute_event.wait()

        result = self.widget.execute_result
        self.widget.execute_result = None
        self.widget.execute_event_lock.release()
        return result

    def remove_item(self, item):
        self.running.wait()
        self.widget.execute_event_lock.acquire()
        self.widget.execute_event.clear()

        self.widget.remove_item_delegate_signal.emit(item)
        self.widget.execute_event.wait()

        self.widget.execute_event_lock.release()

    def add_gird(self, size=None, color=None, antialias=True, glOptions='translucent'):
        param = {
            'size': size,
            'color': color,
            'antialias': antialias,
            'glOptions': glOptions
        }
        item = self.add_item_delegate(gl.GLGridItem, param)
        return item

    def add_scatter(self, pos, color=(1, 1, 1, 1), size=1.5, pxMode=True):
        param = {
            'pos': pos,
            'color': color,
            'size': size,
            'pxMode': pxMode
        }
        item = self.add_item_delegate(gl.GLScatterPlotItem, param)
        return item

    def add_mesh(self,
                 meshdata,
                 faceColor=(1, 1, 1, 1),
                 edgeColor=(1, 1, 1, 1),
                 drawEdges=False,
                 drawFaces=True,
                 shader=None,
                 smooth=False,
                 computeNormals=True):
        param = {
            'meshdata': meshdata,
            'color': faceColor,
            'edgeColor': edgeColor,
            'drawEdges': drawEdges,
            'drawFaces': drawFaces,
            'shader': shader,
            'smooth': smooth,
            'computeNormals': computeNormals
        }
        item = self.add_item_delegate(gl.GLMeshItem, param)
        return item

    def add_line(self, pos, color=(1, 1, 1, 1), width=0.1, antialias=True, mode='line_strip'):
        param = {
            'pos': pos,
            'color': color,
            'width': width,
            'antialias': antialias,
            'mode': mode
        }
        item = self.add_item_delegate(gl.GLLinePlotItem, param)
        return item


def test():
    vis = GPVisualizer()
    item = vis.add_gird()
    item = vis.add_scatter(np.eye(3))
    vis.remove_item(item)
    # result = vis.add_pcloud(np.eye(3), (1,1,1,1), 1)