# ----------------------------------------------------------------------
# quickZoom.py
#
# Copyright (c) 2018 Ingo Clemens, brave rabbit
# www.braverabbit.com
# ----------------------------------------------------------------------

VERSION = {"version": [1, 0, 0], "date": "2018-10-08"}

# ----------------------------------------------------------------------
# Description:
#
# This tool creates a standard dragger context which allows to define a
# region for quickly setting the 2D pan/zoom of the current camera.
#
# ----------------------------------------------------------------------
# Usage:
#
# When properly installed the Maya Modify menu has a new menu item named
# Quick Zoom Tool.
#
# With the tool active drag a region over the area where the camera
# should 2D pan/zoom into.
# Use ctrl+LMB to toggle switch between the standard view and the
# pan/zoom view.
# With pan/zoom active shift+LMB drag with the mouse to pan the view.
#
# Limitations:
# The tool currently does not draw a rectangular marquee which the user
# might expect. This is due to the current limitations of the maya
# python API. This might get addressed in future versions.
#
# Standalone Usage:
# When using the script without the supplementary scripts the tool can
# be activated using the following commands:
#
# # import the module and create the context
# from quickZoom import quickZoomTool
# quickZoomTool.create()
#
# ----------------------------------------------------------------------
# Changelog:
#
#   1.0.0 - 2018-10-08
#         - Initial version.
#
# ----------------------------------------------------------------------

from maya.api import OpenMaya as om2
from maya.api import OpenMayaUI as om2UI
from maya import cmds, mel

import logging

logger = logging.getLogger(__name__)

CONTEXT_NAME = "brQuickZoomContext"
ZOOM_MESSAGE = "<hl>Drag</hl> a region to <hl>zoom/pan</hl> into."
RESET_MESSAGE = "<hl>Ctrl</hl> click to <hl>reset</hl>.  |  <hl>Shift</hl> drag to <hl>pan</hl>."


class QuickZoom():

    def __init__(self):
        self._view = om2UI.M3dView()
        # the camera
        self._mfn = None

        # viewport size
        self._width = 0
        self._height = 0

        # camera settings
        self._ratio = 0
        self._hPan = 0
        self._vPan = 0

        # dragger context
        self._startX = 0
        self._startY = 0
        self._endX = 0
        self._endY = 0


    # ------------------------------------------------------------------
    # context creating and deleting
    # ------------------------------------------------------------------

    def create(self):
        """Create the dragger context and set it to be the active tool.
        """
        helpString = ("Drag a region to zoom/pan into the current view.")
        if not cmds.draggerContext(CONTEXT_NAME, exists=True):
            cmds.draggerContext(CONTEXT_NAME,
                                pressCommand=self._press,
                                dragCommand=self._drag,
                                releaseCommand=self._release,
                                initialize=self._initialize,
                                finalize=self._finalize,
                                space="screen",
                                stepsCount=1,
                                undoMode="step",
                                cursor="default",
                                helpString=helpString,
                                image1="quickZoom.png")
            logger.info("Created {}".format(CONTEXT_NAME))
        cmds.setToolTo(CONTEXT_NAME)


    def delete(self):
        """Delete the dragger context.
        """
        tool = mel.eval("global string $gSelect; setToolTo $gSelect;")
        cmds.deleteUI(CONTEXT_NAME)
        logger.info("Deleted {}".format(CONTEXT_NAME))


    def _message(self, msg):
        """Display the given message as a status in-view message.

        :param msg: The message string to display.
        :type msg: str
        """
        cmds.inViewMessage(statusMessage=msg, position="topCenter")


    def _deleteMessage(self):
        """Delete the in view message.
        """
        cmds.inViewMessage(clear="topCenter")


    def _version(self, long=True):
        """Return the tool version.

        :param long: True, if the version number and date should get
                     returned.
        :type long: bool

        :return: The version string.
        :rtype: str
        """
        version = ".".join([str(i) for i in VERSION["version"]])
        if not long:
            return version
        version = "{} {}".format(version, VERSION["date"])
        return version


    # ------------------------------------------------------------------
    # context commands
    # ------------------------------------------------------------------

    def _press(self):
        """Method to be executed when the mouse button is pressed.

        Get the current camera and it's settings.
        """
        self._view = om2UI.M3dView().active3dView()
        self._mfn = om2.MFnCamera(self._view.getCamera())

        # Exit, if it's not a perspective view.
        if self._mfn.isOrtho():
            logger.warning("Quick Zoom only works in a perspective view.")
            return

        # If the current modifier is the ctrl key toggle the pan/zoom
        # state.
        modifier = cmds.draggerContext(CONTEXT_NAME, query=True, modifier=True)
        if modifier == "ctrl":
            self.togglePanZoom()
            return

        # Get all necessary info about the view and camera settings.
        self._ratio = self._mfn.aspectRatio()
        self._hPan = self._mfn.horizontalPan
        self._vPan = self._mfn.verticalPan
        self._width = float(self._view.portWidth())
        self._height = float(self._view.portHeight())


    def _drag(self):
        """Method to be executed when the mouse is dragged.

        Get the drag points. If the shift modifier is pressed perform a
        2D view panning.
        """
        # get the drag points from the context
        anchorPoint = cmds.draggerContext(CONTEXT_NAME, query=True, anchorPoint=True)
        dragPoint = cmds.draggerContext(CONTEXT_NAME, query=True, dragPoint=True)
        modifier = cmds.draggerContext(CONTEXT_NAME, query=True, modifier=True)

        # store the anchor and drag points
        self._startX = int(anchorPoint[0])
        self._startY = int(anchorPoint[1])
        self._endX = int(dragPoint[0])
        self._endY = int(dragPoint[1])

        # pan the view in case the shift modifier is pressed
        if modifier == "shift" and self._mfn.panZoomEnabled:
            self._pan()


    def _release(self):
        """Method to be executed when the mouse button is released.

        Perform the zooming if no modifier is used.
        """
        modifier = cmds.draggerContext(CONTEXT_NAME, query=True, modifier=True)
        if modifier == "none":
            self._zoomView()
            self._message(RESET_MESSAGE)


    def _initialize(self):
        """Method to be executed when the tool is entered.
        """
        self._message(ZOOM_MESSAGE)


    def _finalize(self):
        """Method to be executed when the tool is exited.
        """
        self._deleteMessage()
        logger.info("Reset {}".format(CONTEXT_NAME))


    # ------------------------------------------------------------------
    # main methods for the calculation
    # ------------------------------------------------------------------

    def _zoomView(self):
        """Set the 2D pan/zoom for the current camera based on the
        dragged region.
        """
        overscan = self._mfn.overscan
        apertureX = self._mfn.horizontalFilmAperture
        apertureY = self._mfn.verticalFilmAperture

        # Depending on the current view type the zoom and pan
        # calculations need different approaches.
        # A horizontal view has additional spaces at the top and bottom
        # whereas a vertical view crops areas to the left and right.
        # Since the 2D pan is defined in inches, relating to the
        # aperture of the camera, these additional spaces need to get
        # respected accordingly and define how the pan is calculated.
        horizontal = self._isHorizontal()

        # Get the effective viewport width and height.
        portWidth = self._width
        portHeight = self._height

        # Since most calculations are dependent on the view type modify
        # the width or height based on the known aspect ratio.
        if horizontal:
            portHeight = portWidth/self._ratio
        else:
            portWidth = portHeight*self._ratio

        # The center of the viewport.
        viewCenterX = portWidth/2.0
        viewCenterY = portHeight/2.0

        # The center of the defined region.
        # The region values are dependent on the view type and have to
        # take the additonal space outside the aspect ratio into
        # consideration.
        dragHalfX = (self._endX-self._startX)/2.0
        dragHalfY = (self._endY-self._startY)/2.0
        if horizontal:
            regionCenterX = dragHalfX+self._startX
            regionCenterY = dragHalfY+self._startY-((self._height-portHeight)/2.0)
        else:
            regionCenterX = dragHalfX+self._startX-((self._width-portWidth)/2.0)
            regionCenterY = dragHalfY+self._startY

        # Calculate the distance between the viewport and region
        # center. This is the basis for the pan calculation.
        deltaCenterX = regionCenterX-viewCenterX
        deltaCenterY = regionCenterY-viewCenterY

        # Calculate an offset factor based on the distance between the
        # viewport and region center and the viewport size, including
        # a possible overscan value.
        offsetX = deltaCenterX/portWidth*overscan
        offsetY = deltaCenterY/portHeight*overscan

        # Lastly, calculate the actual pan values.
        panX = apertureX*offsetX
        panY = apertureY*offsetY

        # Set the attributes on the camera.
        cam = self._mfn.name()
        cmds.setAttr("{}.panZoomEnabled".format(cam), True)
        cmds.setAttr("{}.horizontalPan".format(cam), panX)
        cmds.setAttr("{}.verticalPan".format(cam), panY)
        zoom = self._getZoom()*overscan
        if zoom <= 0:
            zoom = 0.01
        cmds.setAttr("{}.zoom".format(cam), zoom)


    def _isHorizontal(self):
        """Return, if the viewport has a horizontal or vertical fitting.

        This depends on the film fit attribute as well as the size of
        the viewport in case of a fill fitting.

        :return: True, if the viewport type is horizontal.
        :rtype: bool
        """
        horizontal = True
        portRatio = self._width/self._height

        if self._mfn.filmFit == om2.MFnCamera.kFillFilmFit:
            if portRatio < self._ratio:
                horizontal = False
        if self._mfn.filmFit == om2.MFnCamera.kVerticalFilmFit:
            horizontal = False

        return horizontal


    def _getZoom(self):
        """Get the zoom factor based on the dragger region and depending
        on the view type.

        :return: The zoom factor.
        :rtype: float
        """
        start = self._startX
        end = self._endX
        # In case of a vertical view use the dragger Y values for
        # calculating the zoom.
        # By default it's expected that the dragging starts from top to
        # bottom which means that the starting value is larger than the
        # end value. Therefore start and end are reversed.
        if not self._isHorizontal():
            start = self._endY
            end = self._startY

        # Usually the end value is larger than the start value. This is
        # true for dragging along the x axis from left to right.
        if end > start:
            size = end-start
        # If the dragging is performed in the opposite direction (right
        # to left) the values need to be reversed.
        else:
            size = start-end

        # Return the drag size in relation to the width/height of the
        # viewport.
        if self._isHorizontal():
            return size/self._width
        else:
            return size/self._height


    def togglePanZoom(self):
        """Invert the current state of the pan/zoom setting of the
        current camera.
        """
        state = self._mfn.panZoomEnabled
        cmds.setAttr("{}.panZoomEnabled".format(self._mfn.name()), not state)
        if state:
            status = "Deactivated"
            self._message(ZOOM_MESSAGE)
        else:
            status = "Activated"
            self._message(RESET_MESSAGE)
        logger.info("{} Pan/Zoom for camera {}".format(status, self._mfn.name()))


    def _pan(self):
        """Move the 2D pan of the camera based on the distance of the
        dragger context.
        """
        deltaX = self._startX-self._endX
        deltaY = self._startY-self._endY

        cam = self._mfn.name()
        zoom = self._mfn.zoom

        hPan = self._hPan+deltaX*0.00081*zoom
        vPan = self._vPan+deltaY*0.00081*zoom

        cmds.setAttr("{}.horizontalPan".format(cam), hPan)
        cmds.setAttr("{}.verticalPan".format(cam), vPan)

        # Refresh the view to show the new position in the scene.
        cmds.refresh()


quickZoomTool = QuickZoom()

# ----------------------------------------------------------------------
# MIT License
#
# Copyright (c) 2018 Ingo Clemens, brave rabbit
# placeReflection is under the terms of the MIT License
#
# Permission is hereby granted, free of charge, to any person obtaining
# a copy of this software and associated documentation files (the
# "Software"), to deal in the Software without restriction, including
# without limitation the rights to use, copy, modify, merge, publish,
# distribute, sublicense, and/or sell copies of the Software, and to
# permit persons to whom the Software is furnished to do so, subject to
# the following conditions:
#
# The above copyright notice and this permission notice shall be
# included in all copies or substantial portions of the Software.
#
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND,
# EXPRESS OR IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF
# MERCHANTABILITY, FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT.
# IN NO EVENT SHALL THE AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY
# CLAIM, DAMAGES OR OTHER LIABILITY, WHETHER IN AN ACTION OF CONTRACT,
# TORT OR OTHERWISE, ARISING FROM, OUT OF OR IN CONNECTION WITH THE
# SOFTWARE OR THE USE OR OTHER DEALINGS IN THE SOFTWARE.
#
# Author: Ingo Clemens    www.braverabbit.com
# ----------------------------------------------------------------------
