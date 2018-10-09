# ----------------------------------------------------------------------
# placeReflection.py
#
# Copyright (c) 2018 Ingo Clemens, brave rabbit
# www.braverabbit.com
# ----------------------------------------------------------------------

VERSION = {"version": [1, 2, 2], "date": "2018-10-07"}

# ----------------------------------------------------------------------
# Description:
#
# This tool creates a standard dragger context which places the selected
# object at a reflected position based on the view vector and the
# surface normal of a mesh at the cursor position.
# Though any object can be placed this way it's main usage is to easily
# place a light so that the main light reflection occurs at the point
# of the cursor.
#
# The tool has two modes:
# Place Mode: The default dragger context mode. LMB click and drag to
#             place the selected object based on the surface the cursor
#             is dragged over.
# Move Mode: Press and hold Shift or Ctrl while dragging. This moves
#            the object towards/away from the reflection point. Ctrl
#            gives a finer control whereas Shift performs the moving
#            in a faster fashion.
#
# ----------------------------------------------------------------------
# Usage:
#
# When properly installed the Maya Modify menu has a new menu item named
# Place Reflection. It also allows to open a standard option box to set
# the preferences for the tool.
#
# Standalone Usage:
# When using the script without the supplementary scripts the tool can
# be activated using the following commands with the current selection:
#
# # import the module and create the context
# from placeReflection import placeReflectionTool
# placeReflectionTool.create()
#
# ----------------------------------------------------------------------
# Preferences:
#
# The tool has the following preference settings:
#   axis: Defines the axis which is aimed at the point of reflection.
#           Values:
#               0: x axis
#               1: y axis
#               2: z axis (default)
#   invert: True, if the axis should point away from the reflection
#           point. Default is True.
#   rotate: True, if the rotation of the placing obeject should be
#           affected. Default is True.
#   speed: The speed when moving the object towards/away from the
#          reflection point in move mode.
#          Defaults are:
#               0: Slow: 0.001
#               1: Fast: 0.01
#   translate: True, if the translation of the placing object should be
#              affected. Default is True.
#
# When setting these values for the existing context they get stored
# with the Maya preferences:
# placeReflectionTool.setInvert(True)
# placeReflectionTool.setSpeed(0, 0.001) # slow: 0.001
#
# To read the current settings use:
# placeReflectionTool.invert()
# placeReflectionTool.speed(0) # slow
#
# ----------------------------------------------------------------------
# Changelog:
#
#   1.2.2 - 2018-10-07
#         - In case the menu item cannot be added to the modify menu a
#           new menu gets created after the last.
#         - Fixed an incompatibility when calling the tool from another
#           module.
#         - Adjustments to the option box.
#         - Added the quick zoom tool.
#
#   1.2.1 - 2018-10-05
#         - Reversed the speed modifiers shift and ctrl to be more
#           inline with the default Maya navigation (channel box).
#         - Having no placing object selected is now only a warning.
#         - Added a method to read the version.
#
#   1.2.0 - 2018-10-04
#         - Added the option to define the axis which should aim towards
#           the point of reflection.
#         - Added the options to either affect just the translation or
#           the rotation of the placing object.
#         - Added a standard Maya option dialog for setting tool
#           preferences.
#         - Added a menu item in the default Maya modify menu.
#
#   1.1.0 - 2018-10-03
#         - Added a second speed mode which is accesible by pressing the
#           control key (shift: slow, ctrl: fast)
#         - Changed the optionVar names to reflect the new speed
#           settings.
#         - The executing _place() method now directly receives the
#           modifier key instead of just a boolean to turn move mode on
#           or off.
#         - Fixed a stutter during the placing when the placing object
#           moved under the cursor and gets picked as the object to drag
#           on.
#
#   1.0.0 - 2018-10-02
#         - Initial version.
#
# ----------------------------------------------------------------------

from maya.api import OpenMaya as om2
from maya.api import OpenMayaUI as om2UI
from maya import OpenMaya as om
from maya import cmds, mel

import math

import logging

logger = logging.getLogger(__name__)

CONTEXT_NAME = "brPlaceReflectionContext"

AFFECT_TRANSLATION = "brPlaceReflectionAffectTranslation"
AFFECT_ROTATION = "brPlaceReflectionAffectRotation"
INVERT_AXIS = "brPlaceReflectionInvertAxis"
ORIENT_AXIS = "brPlaceReflectionAxis"
SPEED_SLOW = "brPlaceReflectionSpeedSlow"
SPEED_FAST = "brPlaceReflectionSpeedFast"

SPEED_SLOW_VALUE = 0.001
SPEED_FAST_VALUE = 0.01

VIEW_MESSAGE = ("<hl>Drag</hl> to place.  |  "
                "<hl>Shift drag</hl> to move slow.  |  "
                "<hl>Ctrl drag</hl> to move fast.")


class PlaceReflection():

    def __init__(self):
        self._view = om2UI.M3dView()
        self._dag = None
        self._meshDag = None

        # Switch to make sure that values are present when using the
        # move mode.
        self._isSet = False

        # the world point of reflection on the surface
        self._reflPoint = None
        # The distance of the object from the surface.
        # This is used to store the distance during placing as well as
        # moving because the move mode needs a static base value to
        # calculate the new distance from.
        self._dist = 0.0
        # The distance of the object from the surface after moving.
        # This is used to be able to remember the last moved position
        # in case the move mode is performed with a new press and drag
        # operation after the placement. If this value is not stored the
        # new drag would always start from the self._dist position and
        # not from the last known self._moveDist position.
        self._moveDist = 0.0
        # the reflection vector
        self._reflVector = None

        # create the preference settings if they don't exist
        self._setOptionVars()

        self._axis = 2
        self._invert = True
        self._translate = True
        self._rotate = True
        self._speedSlow = 0.001
        self._speedFast = 0.01


    # ------------------------------------------------------------------
    # context creating and deleting
    # ------------------------------------------------------------------

    def create(self):
        """Create the dragger context and set it to be the active tool.
        """
        helpString = ("Press and drag over surface to place the selection. "
                      "Hold ctrl (slow) or shift (fast) to move.")
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
                                cursor="crossHair",
                                helpString=helpString,
                                image1="placeReflection.png")
            logger.info("Created {}".format(CONTEXT_NAME))
        cmds.setToolTo(CONTEXT_NAME)

        # get the preference settings
        self._getOptionVars()


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
    # preferences
    # ------------------------------------------------------------------

    def translate(self):
        """Return if the object's translation is affected.

        :return: The translation state.
        :rtype: bool
        """
        return self._translate


    def setTranslate(self, value):
        """Set if the object's translation is affected.

        :param value: The translation state.
        :type value: bool
        """
        self._translate = value
        cmds.optionVar(intValue=(AFFECT_TRANSLATION, value))


    def rotate(self):
        """Return if the object's rotation is affected.

        :return: The rotation state.
        :rtype: bool
        """
        return self._rotate


    def setRotate(self, value):
        """Set if the object's rotation is affected.

        :param value: The rotate state.
        :type value: bool
        """
        self._rotate = value
        cmds.optionVar(intValue=(AFFECT_ROTATION, value))


    def axis(self):
        """Return the index of the axis which should aim towards the
        point of reflection.

        Values:
            0: X axis
            1: Y axis
            2: Z axis

        :return: The index of the axis.
        :rtype: int
        """
        return self._axis


    def setAxis(self, value):
        """Set the index of the axis which should aim towards the
        point of reflection.

        Values:
            0: X axis
            1: Y axis
            2: Z axis

        :param value: The index of the axis.
        :type value: int
        """
        self._axis = value
        cmds.optionVar(intValue=(ORIENT_AXIS, value))


    def invert(self):
        """Return if the object's aim axis is inverted.

        :return: The invert state.
        :rtype: bool
        """
        return self._invert


    def setInvert(self, value):
        """Set if the object's aim axis is inverted.

        :param value: The invert state.
        :type value: bool
        """
        self._invert = value
        cmds.optionVar(intValue=(INVERT_AXIS, value))


    def speed(self, speedType=0):
        """Return the value for the speed type in move mode.

        Speed type values:
            0: Slow
            1: Fast

        :param speedType: The speed type.
        :type speedType: int

        :return: The speed value.
        :rtype: float
        """
        if speedType == 0:
            return self._speedSlow
        else:
            return self._speedFast


    def setSpeed(self, speedType, value):
        """Set the default value for the given speed type.

        Speed type values:
            0: Slow
            1: Fast

        :param speedType: The move speed type.
        :type speedType: int
        :param value: The speed value to set as the default.
        :type value: float
        """
        if speedType == 0:
            self._speedSlow = value
            cmds.optionVar(floatValue=(SPEED_SLOW, value))
        else:
            self._speedFast = value
            cmds.optionVar(floatValue=(SPEED_FAST, value))


    def _setOptionVars(self, reset=False):
        """Set the preference values.

        :param reset: True, to reset to the default values.
        :type reset: bool
        """
        if reset or not cmds.optionVar(exists=AFFECT_TRANSLATION):
            cmds.optionVar(intValue=(AFFECT_TRANSLATION, 1))

        if reset or not cmds.optionVar(exists=AFFECT_ROTATION):
            cmds.optionVar(intValue=(AFFECT_ROTATION, 1))

        if reset or not cmds.optionVar(exists=INVERT_AXIS):
            cmds.optionVar(intValue=(INVERT_AXIS, 1))

        if reset or not cmds.optionVar(exists=ORIENT_AXIS):
            cmds.optionVar(intValue=(ORIENT_AXIS, 2))

        if reset or not cmds.optionVar(exists=SPEED_SLOW):
            cmds.optionVar(floatValue=(SPEED_SLOW, SPEED_SLOW_VALUE))

        if reset or not cmds.optionVar(exists=SPEED_FAST):
            cmds.optionVar(floatValue=(SPEED_FAST, SPEED_FAST_VALUE))


    def _getOptionVars(self):
        """Get the preference values.
        """
        self._axis = cmds.optionVar(query=ORIENT_AXIS)
        self._invert = cmds.optionVar(query=INVERT_AXIS)
        self._translate = cmds.optionVar(query=AFFECT_TRANSLATION)
        self._rotate = cmds.optionVar(query=AFFECT_ROTATION)
        self._speedSlow = cmds.optionVar(query=SPEED_SLOW)
        self._speedFast = cmds.optionVar(query=SPEED_FAST)


    # ------------------------------------------------------------------
    # context commands
    # ------------------------------------------------------------------

    def _press(self):
        """Method to be executed when the mouse button is pressed.

        Get the current view and object to place.
        """
        self._view = om2UI.M3dView().active3dView()
        # get the MDagPath of the object to place
        self._dag = self._asDagPath()
        if self._dag is None:
            return
        # Set the distance to the last move distance so that the move
        # doesn't start from the original distance but the last modified
        # position.
        self._dist = self._moveDist


    def _drag(self):
        """Method to be executed when the mouse is dragged.

        Get the drag point and perform the placing.
        """
        # do nothing if there is no object selected to be placed
        if self._dag is None:
            return

        # get the drag points from the context and perform the placing
        anchorPoint = cmds.draggerContext(CONTEXT_NAME, query=True, anchorPoint=True)
        dragPoint = cmds.draggerContext(CONTEXT_NAME, query=True, dragPoint=True)
        modifier = cmds.draggerContext(CONTEXT_NAME, query=True, modifier=True)
        self._place(anchorPoint, dragPoint, modifier)


    def _release(self):
        """Method to be executed when the mouse button is released.

        Clear the view and object to place.
        """
        self._view = om2UI.M3dView()
        self._dag = None
        self._meshDag = None


    def _initialize(self):
        """Method to be executed when the tool is entered.
        """
        self._message(VIEW_MESSAGE)


    def _finalize(self):
        """Method to be executed when the tool is exited.

        Mark the context as unused.
        """
        self._moveDist = 0.0
        self._isSet = False
        self._deleteMessage()
        logger.info("Reset {}".format(CONTEXT_NAME))


    # ------------------------------------------------------------------
    # main methods for the calculation
    # ------------------------------------------------------------------

    def _place(self, startPoint, point, modifier):
        """Place the selected object based on the position of the cursor.

        :param startPoint: The starting position of the drag in screen
                           space.
        :type startPoint: list(float)
        :param point: The current drag point in screen space.
        :type point: list(float)
        :param modifier: The name of the modifier key.
        :type modifier: str
        """
        xPos = int(point[0])
        yPos = int(point[1])

        # --------------------------------------------------------------
        # place mode
        # --------------------------------------------------------------
        if modifier == "none":
            # Get the mesh at the cursor position which is used as the
            # reflection base.
            dagPath = self._getMesh(xPos, yPos)
            if dagPath is None:
                return
            self._meshDag = dagPath

            # Convert the screen position of the cursor to a world
            # position.
            worldPt = om2.MPoint()
            worldVector = om2.MVector()
            self._view.viewToWorld(xPos, yPos, worldPt, worldVector)
            # normalize the view vector, just in case
            viewVector = worldVector.normalize()

            # Get the point of the closest intersection between the view
            # ray and the mesh. Returns the tuple:
            # (hitPoint, hitRayParam, hitFace, hitTriangle, hitBary1,
            # hitBary2)
            intersection = self._closestIntersection(dagPath, worldPt, worldVector)
            if not len(intersection[0]):
                return
            # Store the hit point as the point of reflection.
            # This is of type MFloatPoint() (just a reminder because it
            # needs to get converted for other functions).
            self._reflPoint = intersection[0] # MFloatPoint()

            # Get the closest normal of the mesh at the intersection
            # point.
            meshFn = om2.MFnMesh(dagPath)
            result = meshFn.getClosestNormal(om2.MPoint(self._reflPoint), om2.MSpace.kWorld)
            faceNormal = result[0]

            # Calculate the reflection vector.
            self._reflVector = self._reflectionVector(viewVector, faceNormal)

            # Get the current distance of the object intersection point.
            # The reflected position should have the same distance to
            # the surface than before.
            pos = self._translation(self._dag.node())
            self._dist = self._distance(om2.MPoint(self._reflPoint), om2.MPoint(pos))
            self._moveDist = self._dist

            # mark the context as used
            self._isSet = True

        # --------------------------------------------------------------
        # move mode
        # --------------------------------------------------------------
        elif self._isSet:
            speedVal = self._speedSlow
            if modifier == "shift":
                speedVal = self._speedFast
            xPosStart = int(startPoint[0])
            dragDist = (xPos-xPosStart)*speedVal
            self._moveDist = self._dist*(1+dragDist)

        # --------------------------------------------------------------
        # Simply return in case ctrl/shift is pressed during the initial
        # drag. Since no placing has been performed there are no values.
        # --------------------------------------------------------------
        else:
            return

        # Build the transformation matrix from the new postion and
        # rotation.
        mat = self._worldMatrix(self._dag.node())
        transMat = om2.MTransformationMatrix(mat)

        if self._translate:
            # Calculate the reflected vector in world space and scale it
            # by the current distance to the surface.
            placeVector = self._reflVector * self._moveDist + om2.MVector(self._reflPoint)
            transMat.setTranslation(placeVector, om2.MSpace.kWorld)

        if self._rotate:
            # Build the rotation quaternion from the reflection vector.
            quat = self._quatFromVector(self._reflVector)
            transMat.setRotation(quat)

        # Finally, place the object at the reflected position.
        cmds.xform(self._dag.fullPathName(),
                   matrix=self._valueList(transMat.asMatrix()))

        # Refresh the view to show the new position in the scene.
        cmds.refresh()


    def _getMesh(self, xPos, yPos):
        """Return the MDagPath of the object at the cursor position.
        The current selection is left untouched.

        To get the object at the cursor MGlobal.selectFromScreen is used.
        But since this is not available in the new API it's performed
        using the old API and then converted using the full path name.

        :param xPos: The screen-based x position of the cursor.
        :type xPos: int
        :param yPos: The screen-based y position of the cursor.
        :type yPos: int

        :return: The MDagPath of the object at the cursor position.
        :rtype: om2.MDagPath
        """
        sel = om.MSelectionList()
        om.MGlobal.getActiveSelectionList(sel)

        om.MGlobal.selectFromScreen(xPos, yPos, om.MGlobal.kReplaceList,
                                    om.MGlobal.kSurfaceSelectMethod)
        fromScreen = om.MSelectionList()
        om.MGlobal.getActiveSelectionList(fromScreen)

        om.MGlobal.setActiveSelectionList(sel, om.MGlobal.kReplaceList)

        if fromScreen.length():
            dagPath = om.MDagPath()
            fromScreen.getDagPath(0, dagPath)

            # Prevent the case where the object to be placed (for
            # example a light) passes the camera view at the cursor
            # position. The light would get picked as the object under
            # the cursor and the method would return None causing the
            # placing to stutter.
            # Therefore the selected object's name gets checked against
            # the name of the placing object.
            # Important:
            # This needs to happen on a string level because the two
            # APIs are getting mixed here. dagPath is OpenMaya and
            # self._dag is OpenMaya.api.
            # The check is:
            # If the object under the cursor is the same as the placing
            # object and the mesh the context is dragging on is defined
            # it's safe to return the last known mesh name as the mesh
            # to perform the dragging on.
            if dagPath.fullPathName() == self._dag.fullPathName() and self._meshDag is not None:
                return self._meshDag

            dagPath.extendToShape()
            name = dagPath.fullPathName()

            if not dagPath.hasFn(om.MFn.kMesh):
                return

            # converting to maya.api
            return self._asDagPath(name)


    def _closestIntersection(self, dagPath, worldPt, worldVector):
        """Return the closest intersection data for the given mesh with
        the given point and vector.

        :param dagPath: The MDagPath of the mesh object.
        :type dagPath: om2.MDagPath
        :param worldPt: The world point of the ray to test for
                        intersection with.
        :type worldPt: om2.MPoint
        :param worldVector: The MVector of the intersection ray.
        :type worldVector: om2.MVector

        :return: The tuple with the intersection data:
                 hitPoint: The intersection point.
                 hitRayParam: The ray length to the intersection.
                 hitFace: The face index of the intersection.
                 hitTriangle: The relative index of the trangle.
                 hitBary1: First barycentric coordinate.
                 hitBary2: Second barycentric coordinate.
        :rtype: tuple(om2.MFloatPoint, float, int, int, float, float)
        """
        meshFn = om2.MFnMesh(dagPath)

        accelParams = om2.MMeshIsectAccelParams()
        accelParams = meshFn.autoUniformGridParams()

        return meshFn.closestIntersection(om2.MFloatPoint(worldPt),
                                          om2.MFloatVector(worldVector),
                                          om2.MSpace.kWorld,
                                          100000, # maxParam
                                          True)


    def _reflectionVector(self, viewVector, faceNormal):
        """Return the reflection vector based on the given view vector
        and normal at the reflection point.

        :param viewVector: The MVector of the reflection source ray.
        :type viewVector: om2.MVector
        :param faceNormal: The MVector of the normal at the reflection
                           point.
        :type faceNormal: om2.MVector

        :return: The MVector of the reflection.
        :rtype: om2.MVector
        """
        doublePerp = 2.0 * viewVector * faceNormal
        return viewVector - (doublePerp * faceNormal)


    # ------------------------------------------------------------------
    # general functions
    # ------------------------------------------------------------------

    def _asDagPath(self, name=None):
        """Return the dagPath of the node with the given name.
        If the name is None the active selection list is used.

        :param name: The name of the node.
        :type name: str or None

        :return: The dagPath of the node.
        :rtype: om2.MDagPath or None
        """
        sel = om2.MSelectionList()
        if name is None:
            sel = om2.MGlobal.getActiveSelectionList()
        else:
            try:
                sel.add(name)
            except RuntimeError:
                msg = "The node with the name {} does not exist.".format(name)
                raise RuntimeError(msg)
        if sel.length():
            return sel.getDagPath(0)
        else:
            logger.warning("No object selected to place.")


    def _worldMatrix(self, obj):
        """Return the world matrix of the given MObject.

        :param obj: The transform node MObject.
        :type obj: om2.MObject

        :return: The world matrix.
        :rtype: om2.MMatrix
        """
        mfn = om2.MFnDependencyNode(obj)
        matrixObject = mfn.findPlug("worldMatrix", False).elementByLogicalIndex(0).asMObject()
        return om2.MFnMatrixData(matrixObject).matrix()


    def _translation(self, obj):
        """Return the world space translation of the given MObject.

        :param obj: The transform node MObject.
        :type obj: om2.MObject

        :return: The world space translation vector.
        :rtype: om2.MVector
        """
        mat = self._worldMatrix(obj)
        transMat = om2.MTransformationMatrix(mat)
        return transMat.translation(om2.MSpace.kWorld)


    def _distance(self, point1, point2):
        """Return the distance between the two given points.

        :param point1: The first MPoint.
        :type point1: om2.MPoint
        :param point2: The second MPoint.
        :type point2: om2.MPoint

        :return: The distance between the points.
        :rtype: float
        """
        value = 0.0
        for i in range(3):
            value += math.pow(point1[i] - point2[i], 2)
        return math.sqrt(value)


    def _quatFromVector(self, vector):
        """Return a quaternion rotation from the given vector.

        The y axis is used as the up vector.

        :param vector: The vector to build the quaternion from.
        :type vector: om2.MVector

        :return: The rotation quaternion.
        :rtype: om2.MQuaternion
        """
        cross1 = (vector^om2.MVector(0, 1, 0)).normalize()
        cross2 = (vector^cross1).normalize()

        # x axis
        if self._axis == 0:
            xRot = om2.MVector(-vector.x, -vector.y, -vector.z)
            yRot = om2.MVector(-cross2.x, -cross2.y, -cross2.z)
            zRot = cross1
            if self._invert:
                xRot = om2.MVector(-xRot.x, -xRot.y, -xRot.z)
        # y axis
        elif self._axis == 1:
            xRot = om2.MVector(-cross2.x, -cross2.y, -cross2.z)
            yRot = om2.MVector(-vector.x, -vector.y, -vector.z)
            zRot = cross1
            if self._invert:
                yRot = om2.MVector(-yRot.x, -yRot.y, -yRot.z)
        # z axis
        else:
            xRot = cross1
            yRot = om2.MVector(-cross2.x, -cross2.y, -cross2.z)
            zRot = vector
            if self._invert:
                xRot = om2.MVector(-xRot.x, -xRot.y, -xRot.z)
                zRot = om2.MVector(-zRot.x, -zRot.y, -zRot.z)

        mat = om2.MMatrix([xRot.x, xRot.y, xRot.z, 0,
                           yRot.x, yRot.y, yRot.z, 0,
                           zRot.x, zRot.y, zRot.z,
                           0, 0, 0, 0, 1])

        # return the rotation as quaternion
        transMat = om2.MTransformationMatrix(mat)
        return transMat.rotation(True)


    def _valueList(self, mat):
        """Return the given MMatrix as a value list.

        :param matrix: The MMatrix to generate the list from.
        :type matrix: om2.MMatrix

        :return: The list of matrix values.
        :rtype: list(float)
        """
        values = []
        for i in range(4):
            for j in range(4):
                values.append(mat.getElement(i, j))
        return values


placeReflectionTool = PlaceReflection()

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
