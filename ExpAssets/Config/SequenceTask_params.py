### Klibs Parameter overrides ###

#########################################
# Runtime Settings
#########################################
collect_demographics = True
manual_demographics_collection = False
manual_trial_generation = False
run_practice_blocks = True
multi_user = False
view_distance = 57 # in centimeters, 57cm = 1 deg of visual angle per cm of screen
allow_hidpi = True

#########################################
# Available Hardware
#########################################
eye_tracker_available = False
eye_tracking = False

#########################################
# Environment Aesthetic Defaults
#########################################
default_fill_color = (72, 72, 72, 255)
default_color = (255, 255, 255, 255)
default_font_size = 0.45
default_font_unit = 'deg'
default_font_name = 'Roboto-Medium'

#########################################
# Experiment Structure
#########################################
multi_session_project = False
trials_per_block = 120
blocks_per_experiment = 1
table_defaults = {}
conditions = ['PP', 'MI', 'CC']
default_condition = 'PP'

#########################################
# Development Mode Settings
#########################################
dm_trial_show_mouse = False
dm_ignore_local_overrides = False
button_keymap = {
    'w': 'dpup',
    'a': 'dpleft',
    's': 'dpdown',
    'd': 'dpright',
    'i': 'y',
    'j': 'x',
    'k': 'a',
    'l': 'b',
}

#########################################
# Data Export Settings
#########################################
primary_table = "trials"
unique_identifier = "userhash"
exclude_data_cols = ["created"]
append_info_cols = ["random_seed"]
datafile_ext = ".txt"
append_hostname = False

#########################################
# PROJECT-SPECIFIC VARS
#########################################
sequences = {
    'seq1': ["1", "Down", "2", "4", "Down", "Right", "Up"],
    'seq2': ["4", "Right", "1", "4", "Down", "Left", "Up"],
    'seq3': ["Down", "Left", "1", "3", "Up", "Left", "4"],
    'seq4': ["Left", "Down", "1", "2", "Right", "Down", "3"],
    'seq5': ["Right", "Up", "3", "1", "Left", "Down", "2"],
    'seq6': ["Up", "Left", "4", "3", "Right", "Up", "1"],
}

