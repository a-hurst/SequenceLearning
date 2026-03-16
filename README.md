# SequenceLearning

SequenceLearning is a paradigm for studying how we learn complex bimanual sequences. The purpose of the task is to measure how quickly people can reproduce different repeated sequences of movements before and after training.

![SequenceLearning](task.gif)

## Requirements

SequenceLearning is programmed in Python 3.11 using the [KLibs framework](https://github.com/a-hurst/klibs). It has been developed and tested on recent versions of macOS and Linux, but should also work without issue on Windows systems.

To use the task with a gamepad (as intended), you will also need a USB or wireless controller that is supported by your computer. The task has been tested with Microsoft Xbox 360 wired controllers as well as Sony DualShock 4 controllers, but most gamepads that provide a joystick, triggers, and face buttons should work. If no gamepad is available, the WASD and IJKL keys will be used in place of the joystick movements and button presses (respectively) and the spacebar replaces the triggers.


## Getting Started

### Installation

First, you will need to install the KLibs framework by following the instructions [here](https://github.com/a-hurst/klibs).

Then, you can then download and install the experiment program with the following commands (replacing `~/Downloads` with the path to the folder where you would like to put the program folder):

```
cd ~/Downloads
git clone https://github.com/a-hurst/SequenceLearning.git
```

To install all dependencies for the task in a self-contained environment with Pipenv, run `pipenv install` while in the SequenceLearning folder (Pipenv must be already installed).

### Running the Experiment

SequenceLearning is a KLibs experiment, meaning that it is run using the `klibs` command at the terminal (running the 'experiment.py' file using Python directly will not work).

To run the experiment, navigate to the SequenceLearning folder in Terminal and run `klibs run [screensize]`, replacing `[screensize]` with the diagonal size of your display in inches (e.g. `klibs run 21.5` for a 21.5-inch monitor). Note that the stimulus sizes for the study assume that a) the screen size for the monitor has been specified accurately, and b) that participants are seated approximately 57 cm from the screen.

If running the task in a self-contained Pipenv environment, simply prefix all `klibs` commands with `pipenv run` (e.g. `pipenv run klibs run 21.5`).

If you just want to test the program out for yourself and skip demographics collection, you can add the `-d` flag to the end of the command to launch the experiment in development mode. While in development mode, you can also hit the Escape key at any point during the instructions to skip them.

#### Optional Settings

The SequenceLearning paradigm has three possible between-subjects conditions: physical practice (PP), motor imagery (MI), and a semantic control condition (CC).

To choose which condition to run, launch the experiment with the `--condition` or `-c` flag, followed by either `PP`, `MI`, or `CC`. For example, if you wanted to run a participant in the motor imagery condition on a computer with a 15.6-inch monitor, you would run 

```
klibs run 15.6 --condition MI
```

If no condition is manually specified, the experiment program will default to physical practice.
 

### Exporting Data

To export data from the task, simply run

```
klibs export
```

while in the root of the SequenceLearning directory. This will export the trial data for each participant into individual tab-separated text files in the project's `ExpAssets/Data` subfolder.

Reaction time and accuracy data for individual sequence elements and the recall phase can likewise be exported from the data base with `klibs export -t sequences` and `klibs export -t recall`, respectively.
