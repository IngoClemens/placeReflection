# Place Reflection
Maya tool: Perform a reflection-based placement of lights (or any other object) on a mesh.

**placeReflection and quickZoom are under the terms of the MIT License**

### Description:

This tool creates a standard dragger context which places the selected object at a reflected position based on the view vector and the surface normal of a mesh at the cursor position. Though any object can be placed this way it's main usage is to easily place a light so that the light reflection occurs at the point of the cursor.

The tool has two modes:

**Place Mode:**

The default dragger context mode. LMB click and drag to place the selected object based on the surface the cursor is dragged over.


**Move Mode:**

Press and hold Ctrl or Shift while dragging. This moves the object towards/away from the reflection point. Ctrl gives a finer control whereas Shift performs the moving in a faster fashion.

This module also contains the Quick Zoom Tool. Please see the end of this file for a description.

## Installation

For ease of use the script and related files are combined as a module. This allows for an easy installation and keeps all necessary files in one location.

**_Important:_**

**_If after the installation the menu items don't show up it's possible that the downloaded files from github have faulty user permissions. In this case try to create the modules folder manually and check the permissions or download the file from [braverabbit](http://www.braverabbit.com/placereflection/)_**

Copy the module folder from the repository to your Maya preferences. The tool is version independent which means it can be installed in the preferences root folder.

The Maya preferences root directory is located at:

    Windows: C:\Users\USERNAME\Documents\maya
    macOS: /Users/USERNAME/Library/Preferences/Autodesk/maya
    Linux: /home/USERNAME/maya

A default Maya installation doesn't have a modules folder at this specified path. You can directly use the folder from the repository. If the modules folder already exists copy the contents of the repository's modules folder to the one in your preferences.

Inside the modules folder, rename the module template file, which matches your operating system, by removing the current extension. The file should be named placeReflection.mod.

Edit the file in a text editor and replace USERNAME in the path with your user name. Save the file.

Restart Maya. The modify menu in the main menu bar should now contain the menu items Place Reflection Tool and Quick Zoom Tool at the bottom.

## Usage:

When properly installed the Maya Modify menu has a new menu item named Place Reflection Tool. It also allows to open a standard option box to set the preferences for the tool.

# Standalone

When using the script without the supplementary scripts the tool can be activated using the following commands with the current selection:

```
# import the module and create the context
from placeReflection import placeReflectionTool
placeReflectionTool.create()
```

### Preferences:

The tool has the following preference settings:

**axis**
Defines the axis which is aimed at the point of reflection.

Values:
- 0: x axis
- 1: y axis
- 2: z axis (default)

**invert:**
True, if the axis should point away from the reflection point. Default is True.

**rotate**
True, if the rotation of the placing obeject should be affected. Default is True.

**speed:**
The speed when moving the object towards/away from the reflection point in move mode.

Defaults are:
- 0: Slow: 0.001
- 1: Fast: 0.01

**translate**
True, if the translation of the placing object should be affected. Default is True.


#### Setting preferences:
When setting these values for the existing context they get stored with the Maya preferences:

**Example:**

```
placeReflectionTool.setInvert(True)
placeReflectionTool.setSpeed(0, 0.001) # slow: 0.001
```


#### Reading preferences:
To read the current settings use:

```
placeReflectionTool.invert()
placeReflectionTool.speed(0) # slow
```


### Latest version: 1.2.3 (2018-10-09)


## Changelog:

**1.2.3 (2018-10-09)**

    - Added an in-view message when the tool is active.

**1.2.2 (2018-10-07)**

    - In case the menu item cannot be added to the modify menu a new menu gets created after the last.
    - Fixed an incompatibility when calling the tool from another module.
    - Adjustments to the option box.
    - Added the quick zoom tool.

**1.2.1 (2018-10-05)**

    - Reversed the speed modifiers shift and ctrl to be more inline with the default Maya navigation (channel box).
    - Having no placing object selected is now only a warning.
    - Added a method to read the version.

**1.2.0 (2018-10-04)**

    - Added the option to define the axis which should aim towards the point of reflection.
    - Added the options to either affect just the translation or the rotation of the placing object.
    - Added a standard Maya option dialog for setting tool preferences.
    - Added a menu item in the default Maya modify menu.

**1.1.0 (2018-10-03)**

    - Added a second speed mode which is accesible by pressing the control key (shift: slow, control: fast)
    - Changed the optionVar names to reflect the new speed settings.
    - The executing _place() method now directly receives the modifier key instead of just a boolean to turn move mode on or off.
    - Fixed a stutter during the placing when the object to place moved under the cursor and gets picked as the object to drag on.

**1.0.0 (2018-10-02)**

    - Initial version.


# Quick Zoom
Maya tool: This tool creates a standard dragger context which allows to define a region for quickly setting the 2D pan/zoom of the current camera.

## Usage:

When properly installed the Maya Modify menu has a new menu item named Quick Zoom Tool.

With the tool active drag a region over the area where the camera should 2D pan/zoom into. Use ctrl+LMB to toggle switch between the standard view and the pan/zoom view. With pan/zoom active shift+LMB drag with the mouse to pan the view.

**Limitations:**

The tool currently does not draw a rectangular marquee which the user might expect. This is due to the current limitations of the maya python API. This might get addressed in future versions.

# Standalone

When using the script without the supplementary scripts the tool can be activated using the following commands:

```
# import the module and create the context
from quickZoom import quickZoomTool
quickZoomTool.create()
```
