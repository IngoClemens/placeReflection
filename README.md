# placer
Maya tool: Perform a reflection-based placement of lights (or any other object) on a mesh.

**placer is under the terms of the MIT License**

### Description:

This tool creates a standard dragger context which places the selected object at a reflected position based on the view vector and the surface normal of a mesh at the cursor position. Though any object can be placed this way it's main usage is to easily place a light so that the main light reflection occurs at the point of the cursor.

The tool has two modes:

**Place Mode:**

The default dragger context mode. LMB click and drag to place the selected object based on the surface the cursor is dragged over.


**Move Mode:**

Press and hold Shift or Control while dragging. This moves the object towards/away from the reflection point. Shift gives a finer control whereas control performs the moving in a faster fashion.

### Usage:

Select the object which should be placed and run the commands.

```
#import the module and create the context
from placer import placerContext
placerContext.create()
```

### Preferences:

The tool has two preference settings:

**invert:**

True, if the z axis should point away from the reflection point. Default is True.


**speed:**

The increment size when moving the object towards/away from the reflection point in move mode.

Defaults are:
- 0: Slow: 0.001
- 1: Fast: 0.01


When setting these values for the existing context they get stored with the Maya preferences:

Example:

placerContext.setInvert(True)

placerContext.setSpeed(0, 0.001) # slow: 0.001


To read the current settings use:

placerContext.invert()

placerContext.speed(0) # slow

## Latest version: 1.1 (2018-10-03)
