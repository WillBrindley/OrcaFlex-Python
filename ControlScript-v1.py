"""
This module is a  Python external function for use with OrcaFlex.
It creates a GUI, which controls OrcaFlex model objects dynamicaly
To allow the graphics to update during simulation, set dynamic refresh interval to 50 ms: OrcaFlex -> Tools -> 3D View -> Refresh interval (ms)
The model must be simple and efficient to run in real time. Line element size, implicit time step and Rayleigh damping adjustments may be needed.
If the model runs too fast, the sleep() function can be used to slow the simulation down to real time speed
"""

# Installation required for PySimpleGUI.
# The easiest way is: Command Prompt -> pip install PySimpleGUI
import PySimpleGUI as gui
import sys
import numpy

class OffsetControl(object):

    def Initialise(self, info):
        # In the Calculate() method we ask OrcaFlex for the model data, and
        # to do this we'll need an OrcFxAPI.Period to say we want the value 'now':
        self.periodNow = OrcFxAPI.Period(OrcFxAPI.pnInstantaneousValue)

        # Settings for outputting results to external output at a set period in seconds
        self.StartTime = 1
        self.TimeStep = info.Model['General'].ImplicitConstantTimeStep

        # Control object names in the OrcaFlex model
        self.OffsetMaster = "ShaftOffset-Controlled"
        self.SupportMaster = "MoveSupport-Controlled"

        # Input to define the scale for the GUI. [Piston offset, Support offset, tension]
        self.GUItext = ['Cam Offset (mm)', 'Support Offset (m)']
        self.ScaleMax = [150, 3.0]     # Scale maximum. Units: mm, m
        self.ScaleMin = [0, 0]           # Scale minimum. Units: mm, m
        self.RateMaxList = [0.02, 0.30]      # Maximum rate of cchange. Units: m/s. Note tension does not need to be gradually changed.
        self.ScaleRes = [1, 0.01]        # Slider scale resolution. Units: mm, m
        
        # Control settings for changing piston offset
        if info.ModelObject.Name == self.OffsetMaster:
            self.RateMax = self.RateMaxList[0]                  # m per second
            self.RateStep = self.RateMax * self.TimeStep        # m per time step
            self.maxOffset = self.ScaleMax[0] / 1000            # Defines the upper limit of the control slider scale in m
            self.TargetOffset = self.ScaleMin[0] / 1000                       
            self.TargetOffsetScale = 0
            info.Workspace['camdata'] = self.TargetOffsetScale      # Workspace allows sharing of data between model objects

        # Control settings for changing support offset
        if info.ModelObject.Name == self.SupportMaster:
            self.RateMax = self.RateMaxList[1]                  # m per second
            self.RateStep = self.RateMax * self.TimeStep        # m per time step
            self.maxOffset = self.ScaleMax[1]                   # Defines the upper limit of the control slider scale
            self.TargetOffset = self.ScaleMin[1] 
            self.TargetOffsetScale = 0
            info.Workspace['supportdata'] = self.TargetOffsetScale  # Workspace allows sharing of data between model objects

        # Define the PySimpleGUI slider
        # We only want to trigger the GUI once to create a single interface window. Workspace is used to share data between mode objects.
        if info.ModelObject.Name == self.OffsetMaster:  
            gui.theme('DarkAmber') 
            layout = [
                [gui.Text(self.GUItext[0])],
                [gui.Slider(range=(self.ScaleMin[0], self.ScaleMax[0]), default_value=self.ScaleMin[0], resolution=self.ScaleRes[0], size=(15, 15), orientation="v",
                            enable_events=True, key="cam")],
                [gui.Text(self.GUItext[1])],
                [gui.Slider(range=(self.ScaleMin[1], self.ScaleMax[1]), default_value=self.ScaleMin[1], resolution=self.ScaleRes[1], size=(15, 15), orientation="v",
                            enable_events=True, key="support")]            
            ]
            self.window = gui.Window("slider GUI", layout)          


    def Calculate(self, info):

        # Only run for new time steps
        if not info.NewTimeStep:
            return

        # Read data from the control slider GUI. This will only be done for one model object, so we need to share values in workspace.
        if info.ModelObject.Name == self.OffsetMaster:
            # Read data from the GUI slider if it is changed (an event). If no event after 0.01 seconds, then continue the code.
            event, values = self.window.Read(timeout=10)    
            # Exits the program if exit selected on the window
            if event in  (None, 'Exit'):
                sys.exit()       
            # Record the result if there is an input change.
            if event is not None:
                if event == "cam":
                    info.Workspace['camdata'] = values["cam"]
                if event == "support":
                    info.Workspace['supportdata'] = values["support"]                  
                    
        # Define the target offset position and tension
        if info.ModelObject.Name == self.OffsetMaster:
            self.TargetOffsetScale = info.Workspace['camdata']
            self.TargetOffset = self.TargetOffsetScale / 1000       
        if info.ModelObject.Name == self.SupportMaster:
            self.TargetOffsetScale = info.Workspace['supportdata']
            self.TargetOffset = self.TargetOffsetScale

        # Only start after the specified time
        if info.SimulationTime < self.StartTime:
            return

        # Calculate the change in X-offset position 
        # Find the position error from the defined target position
        self.PositionLast = info.StructValue.Position[0]
        self.PositionError = self.PositionLast - self.TargetOffset
        self.ErrorDir = numpy.sign(self.PositionError)
        # Get the position change required for the time step 
        if abs(self.PositionError) > self.RateStep:
            PositionNew = self.PositionLast - (self.RateStep * self.ErrorDir)
        else:
            if info.ModelObject.Name == self.SupportMaster:
                PositionNew = self.PositionLast 
            else: PositionNew = self.PositionLast - (self.PositionError * self.ErrorDir)

        # Return the X position to feed into the model
        info.StructValue.Position[0] = PositionNew


    # Close the GUI window on reset                     
    def Finalise(self, info):
        self.window.close()


