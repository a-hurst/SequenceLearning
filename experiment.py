# -*- coding: utf-8 -*-

__author__ = "Austin Hurst"

import itertools
from math import sqrt
from random import choice, shuffle

import sdl2
import numpy
import klibs
from klibs import P
from klibs.KLExceptions import TrialException
from klibs.KLGraphics import fill, flip, blit
from klibs.KLGraphics import KLDraw as kld
from klibs.KLGraphics.KLNumpySurface import NumpySurface
from klibs.KLEventQueue import flush, pump
from klibs.KLUtilities import angle_between, point_pos, deg_to_px, px_to_deg
from klibs.KLUtilities import line_segment_len as linear_dist
from klibs.KLTime import CountDown
from klibs.KLText import add_text_style, TextStyle
from klibs.KLCommunication import message
from klibs.KLUserInterface import any_key, mouse_pos, ui_request, hide_cursor
from sdl2.ext import get_key_state

from gamepad import gamepad_init, button_pressed, ControllerButton, VirtualButton
from gamepad_usb import get_all_controllers
from picodraw import (
    draw_arrow, draw_circle, draw_square, draw_star, draw_asterisk, draw_squircle
)


# Define colours for use in the experiment
WHITE = (255, 255, 255)
LIGHT_GREY = (192, 192, 192)
BLACK = (0, 0, 0)
MIDGREY = (128, 128, 128)
TRANSLUCENT_RED = (255, 0, 0, 96)
TRANSLUCENT_BLUE = (0, 0, 255, 96)
NICE_RED = (224, 121, 110)
NICE_GREEN = (82, 182, 75)

# Colour blind palettes from ggpubfigs
IBM_PALETTE = [
    (128, 163, 248),
    (137, 122, 235),
    (211, 79, 143),
    (238, 127, 49),
    (245, 192, 46),
]
TABLEAU_TEN = [
    (78, 121, 167),
    (242, 142, 43),
    (225, 87, 89),
    (118, 183, 178),
    (89, 161, 79),
    (237, 201, 72),
    (176, 122, 161),
    (255, 157, 167),
    (156, 117, 95),
    (186, 176, 172),
]


# Define constants for working with gamepad data
AXIS_MAX = 32768
TRIGGER_MAX = 32767



class SequenceTask(klibs.Experiment):

    def setup(self):

        # Initialize gamepad (if present)
        self.gamepad = None
        gamepad_init()
        controllers = get_all_controllers()
        if len(controllers):
            self.gamepad = controllers[0]
            self.gamepad.initialize()
            print(self.gamepad._info)

        # Initialize stimulus sizes and layout
        self.item_offset = deg_to_px(2.2) # spacing between elements
        item_w = deg_to_px(1.5) # sequence element width
        fix_size = deg_to_px(0.5) # fixation shape size
        fix_t = deg_to_px(0.12) # fixation thickness (plus sign)
        arrow_t = deg_to_px(0.3) # arrow thickness
        cell_size = deg_to_px(2.0) # size of squares for recall phase
        self.block_msg_loc = (P.screen_c[0], int(P.screen_y * 0.4))
        self.lower_middle = (P.screen_c[0], int(P.screen_y * 0.75))

        # Initialize custom text styles
        add_text_style("wrong", size='1.0deg', color=NICE_RED)
        add_text_style("feedback", size='0.7deg')
        add_text_style("progress", color=(255, 255, 255, 128))

        # Define maps between inputs and input names
        self.stick_map = {
            0: None,
            1: "Up",
            #2: "Up-Right",
            3: "Right",
            #4: "Down-Right",
            5: "Down",
            #6: "Down-Left",
            7: "Left",
            #8: "Up-Left",
        }
        self.buttonmap = {
            "x": "1",
            "y": "2",
            "b": "3",
            "a": "4",
        }
        if P.allow_dpad or not self.gamepad:
            self.buttonmap.update({
                "dpup": "Up",
                "dpdown": "Down",
                "dpleft": "Left",
                "dpright": "Right",
            })

        # Generate task stimuli
        self.fixations = {
            'circle': draw_circle(fix_size, MIDGREY),
            'diamond': draw_square(fix_size / sqrt(2), MIDGREY, angle=45),
            'star': draw_star(fix_size, MIDGREY),
            'plus': draw_asterisk(fix_size, fix_t, MIDGREY, spokes=4)
        }
        self.icons = {
            "Left": draw_arrow(item_w, item_w, arrow_t, WHITE, angle=0),
            "Up": draw_arrow(item_w, item_w, arrow_t, WHITE, angle=90),
            "Right": draw_arrow(item_w, item_w, arrow_t, WHITE, angle=180),
            "Down": draw_arrow(item_w, item_w, arrow_t, WHITE, angle=270),
            "1": draw_button(item_w, "1", color=TABLEAU_TEN[0]),
            "2": draw_button(item_w, "2", color=TABLEAU_TEN[1]),
            "3": draw_button(item_w, "3", color=TABLEAU_TEN[2]),
            "4": draw_button(item_w, "4", color=TABLEAU_TEN[4]),
        }
        self.cell = draw_squircle(cell_size, MIDGREY, radius=0.4)
        self.icons_grey = {}
        for name, stim in self.icons.items():
            new_stim = stim.copy()
            new_stim[:, :, 3] = new_stim[:, :, 3] * 0.5
            self.icons_grey[name] = new_stim

        # Define error messages for the task
        err_txt = {
            "too_soon": (
                "Too soon!\nPlease wait for the sequence to appear before responding."
            ),
            "too_fast": (
                "Too fast!\nPlease practice the full sequence before responding."
            ),
            "too_slow": "Too slow!\nPlease try to complete the sequence faster.",
            "start_triggers": (
                "Please fully release the triggers before the start of each trial."
            ),
            "repeat_err": (
                "Too many incorrect responses!\nPlease try to respond more carefully."
            ),
            "mi_button": (
                "Button pressed!\n"
                "Please try to only *imagine* pressing buttons in this phase of the task."
            ),
            "cc_button": (
                "Button pressed!\n"
                "Please avoid moving as you silently repeat the names of the items."
            )
        }
        self.errs = {}
        for key, txt in err_txt.items():
            self.errs[key] = message(txt, align="center")

        # Initialize runtime variables
        self.practiced_seqs = self.exp_factors["seq_name"]
        self.seq_history = []
        self._triggers_down = False

        # Create fixation map for training block
        training_fixations = ['diamond', 'star', 'plus']
        self.fixation_map = {}
        for seq in self.practiced_seqs:
            self.fixation_map[seq] = training_fixations.pop()

        # Run task tutorial (can skip by pressing Esc)
        try:
            self.task_tutorial()
        except SkipInstructions:
            pass


    def task_tutorial(self):
        stim = self.get_demo_stim()
        progress = ProgressMessage(
            "Instructions: {0} / {1}", total=6, textstyle='progress', autotick=True
        )
        self.show_demo_text(
            "Welcome to the experiment! This tutorial will help explain the task.",
            stim['fixation'] + [progress],
        )
        self.show_demo_text(
            ("On each trial of the experiment, you will be shown a sequence of "
             "arrows and numbers."),
            stim['seq'] + [progress],
        )
        self.show_demo_text(
            ["Each sequence item corresponds to an input on the game controller.",
            "Arrows (Up, Down, Left, Right) represent movements with the left stick:"],
            stim['arrows'] + [progress],
        )
        self.show_demo_text(
            ("Numbers (1, 2, 3, 4) represent button presses on the right side of "
             "the controller:"),
            stim['numbers'] + [progress],
        )
        self.show_demo_text(
            ("The numbers are mapped to buttons in clockwise order, as "
             "illustrated below:"),
            stim['buttons'] + [progress],
        )
        self.show_demo_text(
            ("Each sequence is made of numbers (button presses) and arrows (stick "
             "movements).\nYour job will be to repeat these sequences yourself using "
             "the game controller."),
            stim['seq'] + [progress],
        )
        self.input_demo()
        self.show_demo_text(
            ["Input demo complete!",
             "Press any button to start the next phase of instructions."],
            [], msg_y = int(P.screen_y * 0.45)
        )
        progress = ProgressMessage(
            "Instructions: {0} / {1}", total=4, textstyle='progress', autotick=True
        )
        self.show_demo_text(
            ("Now that you have a feel for the basics, let's try practicing some "
             "simple sequences."),
            stim['pair'] + [progress],
        )
        self.show_demo_text(
            ("Each sequence will be a pair of items. Simply respond to each item in "
             "order\n(not at the same time!) and then squeeze the rear triggers to "
             "continue."),
            stim['pair'] + [progress],
        )
        self.show_demo_text(
            ("Don't worry about going quickly, just focus on making the right "
             "movements!"),
            stim['pair'] + [progress],
        )
        self.show_demo_text(
            ["If you make a mistake, you will be shown feedback to let you know.",
             "If this happens, just take a deep breath and try again."],
            stim['pair_err'] + [progress],
        )
        self.show_demo_text(
            "When you're ready, press any button to begin.", [],
            duration=1.0, msg_y=int(P.screen_y * 0.4)
        )
        self.pairs_practice()
        self.show_demo_text(
            ["Pair practice complete!",
             "Press any button to start the next phase of instructions."],
            [], msg_y = int(P.screen_y * 0.45)
        )


    def practice_instructions(self):
        stim = self.get_demo_stim()
        progress = ProgressMessage(
            "Instructions: {0} / {1}", total=7, textstyle='progress', autotick=True
        )
        self.show_demo_text(
            ("Now that you have some practice with the controls, let's try some "
             "full sequences!"),
            stim['fixation'] + [progress],
        )
        self.show_demo_text(
            ("Each trial starts with a row of shapes, showing you where the sequence "
             "is about to appear:"),
            stim['fixation'] + [progress],
        )
        self.show_demo_text(
            ("When the sequence appears, try to quickly perform the sequence of "
             "movements\nyourself by using the joystick and buttons on the game "
             "controller."),
            stim['seq_grey'] + [progress],
        )
        self.show_demo_text(
            ("The icons will light up as you make each movement in the sequence, "
             "letting you know\nyou responded correctly and showing your progress."),
            stim['seq_progress'] + [progress],
        )
        self.show_demo_text(
            ("If the next icon does *not* light up when you make a movement, this "
             "means that your last\ninput was either wrong or didn't register. If this "
             "happens, simply try the input again."),
            stim['seq_progress'] + [progress],
        )
        self.show_demo_text(
            ("Once you have responded to all items in the sequence, squeeze both "
             "triggers at once\non the back of the controller to end the trial."),
            stim['seq'] + [progress],
        )
        self.show_demo_text(
            ("At the end of each trial, you will be given feedback on your speed and "
             "accuracy.\nPlease try to complete the sequences as quickly as you can "
             "without making mistakes!"),
            stim['feedback'] + [progress],
        )

    def training_instructions(self):
        stim = self.get_demo_stim()
        instr_counts = {'PP': 11, 'MI': 11 + 6, 'CC': 11 + 5}
        progress = ProgressMessage(
            "Instructions: {0} / {1}", total=instr_counts[P.condition],
            textstyle='progress', autotick=True
        )
        self.show_demo_text(
            ("Now that you've gotten some practice, in this next phase of the study "
             "you will train on\n3 sequences repeatedly to see how much you can "
             "improve your performance!"),
            stim['fixation'] + [progress],
        )

        if P.condition == "MI":
            self.training_instructions_mi(progress)
        elif P.condition == "CC":
            self.training_instructions_cc(progress)

        self.show_demo_text(
            ("In this training block, each of the three sequences will start with a "
             "different row of shapes."),
            stim['fixation'] + [progress],
        )
        self.show_demo_text(
            "One sequence will start with diamonds:",
            stim['fix_diamond'] + [progress],
        )
        self.show_demo_text(
            "Another sequence will start with stars:",
            stim['fix_star'] + [progress],
        )
        self.show_demo_text(
            "And the third sequence will start with plus signs:",
            stim['fix_plus'] + [progress],
        )
        self.show_demo_text(
            ("You can use these shapes to help prepare for each sequence before "
             "it appears!"),
            stim['fix_plus'] + [progress],
        )
        self.show_demo_text(
            ("At the end of the study, you will be tested on how *quickly and "
             "accurately*\nyou can perform each of the three sequences."),
            stim['seq_grey'] + [progress],
        )
        self.show_demo_text(
            ("Because this is a *training* phase, your goal is to practice the "
             "sequences in order\nto perform as well as you can in the final "
             "test block."),
            stim['seq_grey'] + [progress],
        )
        self.show_demo_text(
            ("In other words, we want you to focus on improving your *future* sequence "
             "performance\ninstead of trying to practice as quickly as you can "
             "right now."),
            stim['seq_grey'] + [progress],
        )
        self.show_demo_text(
            ("If you think going slowly through the sequence items would help more\n"
             "in the long run, please take your time!"),
            stim['seq_grey'] + [progress],
        )
        self.show_demo_text(
            ("As you practice the sequences, you will be regularly updated on\n"
             "your progress and have the chance to take breaks."),
            stim['seq_grey'] + [progress],
        )

    def training_instructions_mi(self, progress):
        stim = self.get_demo_stim()
        self.show_demo_text(
            ("During this block, instead of performing sequences of movements "
             "*physically*,\nplease rehearse the sequences *mentally* using motor "
             "imagery."),
            stim['seq_grey'] + [progress],
        )
        self.show_demo_text(
            ("This means that instead of physically pressing buttons or moving the "
             "joystick, try to\nsimply *imagine* the movements you would need to make "
             "for each sequence."),
            stim['seq_grey'] + [progress],
        )
        self.show_demo_text(
            ("For example, you might visualize how your right thumb would move "
             "between the 2, 1,\n& 3 buttons, then imagine using your left thumb to "
             "move the stick right, up, down, & left."),
            stim['seq_grey'] + [progress],
        )
        self.show_demo_text(
            ("If it helps, you can try to visualize the icons lighting up and simulate "
             "how each\nmovement would *feel* as you move through the sequence in "
             "your mind."),
            stim['seq_grey'] + [progress],
        )
        self.show_demo_text(
            ("Please try to avoid actually moving your hands and keep your thumbs\n"
             "relaxed as you imagine performing the movements."),
            stim['seq_grey'] + [progress],
        )
        self.show_demo_text(
            ("Once you have completed the sequence in your mind, please squeeze\n"
             "the rear triggers *physically* to end the trial."),
            stim['seq_grey'] + [progress],
        )

    def training_instructions_cc(self, progress):
        stim = self.get_demo_stim()
        self.show_demo_text(
            ("During this block, instead of performing sequences of movements "
             "*physically*,\nplease rehearse the sequences *mentally* by repeating "
             "them silently in your head."),
            stim['seq_grey'] + [progress],
        )
        self.show_demo_text(
            ("For example, you would practice the sequence below by repeating "
            "“two, one, three, right,\nup, down, left” to yourself silently, and "
            "then squeezing the triggers to end the trial."),
            stim['seq_grey'] + [progress],
        )
        self.show_demo_text(
            ("Please try and keep your hands still and avoid actual movement during "
             "mental rehearsal.\nSimply focus on trying to memorize each sequence by "
             "rehearsing the names of its items."),
            stim['seq_grey'] + [progress],
        )
        self.show_demo_text(
            ("Please remember to rehearse the items *silently*. Try not to actually "
             "say them out loud!"),
            stim['seq_grey'] + [progress],
        )
        self.show_demo_text(
            ("For the sake of the experiment, please only rehearse each sequence once "
             "per trial.\nYou will have plenty of chances to practice each sequence, "
             "so don't worry!"),
            stim['seq_grey'] + [progress],
        )

    def recall_instructions(self):
        stim = self.get_demo_stim()
        progress = ProgressMessage(
            "Instructions: {0} / {1}", total=5, textstyle='progress', autotick=True
        )
        self.show_demo_text(
            [("Training complete! Before we begin the test phase, we want to check how "
             "well you\ncan remember the items of the three sequences you practiced."),
             "Please put the controller down and press the space bar to continue."],
            [], msg_y = int(P.screen_y * 0.4)
        )
        self.show_demo_text(
            ("For each unique starting shape (diamond, star, or plus), you will be "
             "asked to try and\nremember the corresponding sequence to the best of "
             "your memory."),
            stim['recall_cells'] + [progress],
            msg_y = int(P.screen_y * 0.2)
        )
        self.show_demo_text(
            ("Instead of using the controller, please enter the sequences using\n"
             "the *number and arrow keys* on the keyboard."),
            stim['recall_cells'] + stim['seq_recall'] + [progress],
            msg_y = int(P.screen_y * 0.2)
        )
        self.show_demo_text(
            ("This section is not timed, so don't worry about answering quickly!\nJust "
             "do your best to remember the items for each sequence."),
            stim['recall_cells'] + stim['seq_recall'] + [progress],
            msg_y = int(P.screen_y * 0.2)
        )
        self.show_demo_text(
            ("Don't worry if you haven't fully memorized a sequence, it's okay if "
             "you don't remember\nperfectly. If you can't remember an item just "
             "take a guess!"),
            stim['recall_cells'] + stim['seq_recall'] + [progress],
            msg_y = int(P.screen_y * 0.2)
        )
        self.show_demo_text(
            ("If you make a mistake typing the sequence, press the Backspace key to "
             "undo the\nprevious item. When you are ready to submit, press the "
             "Enter key."),
            stim['recall_cells'] + stim['seq_recall2'] + [progress],
            msg_y = int(P.screen_y * 0.2)
        )

    def test_instructions(self):
        stim = self.get_demo_stim()
        progress = ProgressMessage(
            "Instructions: {0} / {1}", total=5, textstyle='progress', autotick=True
        )
        self.show_demo_text(
            ("Welcome to the final phase of the experiment! In this section, you "
             "will be tested on\nhow quickly and accurately you can perform the "
             "sequences you practiced."),
            stim['fixation'] + [progress],
        )
        self.show_demo_text(
            ("For this phase, please perform the sequences physically using the game "
             "controller.\nYou will receive feedback on your accuracy and response "
             "times."),
            stim['seq_grey'] + [progress],
        )
        self.show_demo_text(
            ("Note that this block contains 6 different sequences: the 3 you practiced "
             "during the training\nphase, and 3 unpracticed sequences. Try your "
             "best to perform well on all of them!"),
            stim['seq_grey'] + [progress],
        )
        self.show_demo_text(
            "In this block, the starting row of shapes is the same for all sequences.",
            stim['fixation'] + [progress],
        )
        self.show_demo_text(
            ("At the end of each trial, you will be given feedback on your speed and "
             "accuracy.\nPlease try to complete the sequences as quickly as you can "
             "without making mistakes!"),
            stim['feedback'] + [progress],
        )


    def block(self):

        block_msgs = {
            "practice": (
                "When you're ready, press any button to begin the practice phase.\n"
                "Remember to try and avoid mistakes!"
            ),
            "training_PP": (
                "When you're ready, press any button to begin the training phase.\n"
                "Remember to focus on practicing for the final block!"
            ),
            "training_MI": (
                "When you're ready, press any button to begin the training phase.\n"
                "Remember to keep your thumbs relaxed as you rehearse the movements "
                "mentally!"
            ),
            "training_CC": (
                "When you're ready, press any button to begin the training phase.\n"
                "Remember to keep your thumbs relaxed as you rehearse the item names "
                "mentally!"
            ),
            "test": (
                "When you're ready, press any button to begin the test phase.\n"
                "Remember to try and avoid mistakes!"
            ),
        }

        # If starting the final block, run requence recall
        if self.block_label == "test":
            self.run_seqence_recall()

        # Show block instructions
        try:
            if self.block_label == "practice":
                self.practice_instructions()
            if self.block_label == "training":
                block_msg = block_msgs["training_" + P.condition]
                self.training_instructions()
            elif self.block_label == "test":
                self.test_instructions()
        except SkipInstructions:
            pass
        
        # Show block start message
        if self.block_label == "training":
            block_msg = block_msgs["training_" + P.condition]
        else:
            block_msg = block_msgs[self.block_label]
        msg = message(block_msg, align="center")
        msg2 = message("Press any button to start.")
        self.show_feedback(msg, duration=2.0, location=self.block_msg_loc)
        fill()
        blit(msg, 5, self.block_msg_loc)
        blit(msg2, 5, self.lower_middle)
        flip()
        wait_for_input(self.gamepad)


    def trial_prep(self):
    
        if self.block_label == "training":
            self.trial_type = P.condition
            fixation_shape = self.fixation_map[self.seq_name]
            self.fixation = self.fixations[fixation_shape]
            self.seq_history.append(self.seq_name)
        else:
            self.trial_type = "PP"
            self.fixation = self.fixations['circle']

        if self.seq_name == "random":
            self.seq_type = "random"
            icon_list = list(self.icons.keys())
            self.sequence = random_choices(icon_list, n=7)
        else:
            practiced = self.seq_name in self.practiced_seqs
            self.seq_type = "practiced" if practiced else "unpracticed"
            self.sequence = P.sequences[self.seq_name]

        # Add timecourse of events to EventManager
        self.evm.add_event('sequence_on', onset=1000)
        self.evm.add_event('timeout', onset=15000, after='sequence_on')

        # Reset input state
        self._triggers_down = False
        self._stick_prev_direction = 0

        # Ensure triggers released prior to trial start
        while True:
            if self.triggers_released():
                break
            self.show_feedback(self.errs["start_triggers"], duration=0.5)


    def trial(self):

        # Initialize trial variables
        seq = self.sequence
        responses = []
        progress = 0
        num_wrong = 0
        total_errs = 0
        err = "NA"
        done = False

        # Show fixation stimuli prior to sequence onset
        while self.evm.before("sequence_on"):
            fill()
            draw_sequence([self.fixation], self.item_offset, count=len(seq))
            flip()
            # If any responses prior to sequence onset, end trial w/ error
            resp, timestamp = self.get_sequence_input()
            if resp:
                err = "too_soon"
                done = True
                break
        
        # Iterate over sequence elements until sequence complete (or error)
        start = None
        prev_time = None
        while not done:

            # Draw sequence stimuli to screen
            complete = [self.icons[e] for e in seq[:progress]]
            remaining = [self.icons_grey[e] for e in seq[progress:]]
            fill()
            draw_sequence(complete + remaining, self.item_offset)
            flip()
            if not start:
                start = sdl2.SDL_GetTicks()
                prev_time = start
            
            # Determine the next input in the sequence
            if self.trial_type == "PP" and progress < len(seq):
                target = seq[progress]
            else:
                target = "triggers"
        
            # Wait for next sequence element to be input correctly
            response = None
            while response != target:
                response, timestamp = self.get_sequence_input()
                if response:
                    resp = {
                        'participant_id': P.participant_id,
                        'block_num': P.block_number,
                        'trial_num': P.trial_number,
                        'seq_name': self.seq_name,
                        'index': progress + 1,
                        'element': target,
                        'response': response,
                        'rt': timestamp - prev_time,
                        'acc': response == target,
                        'n_attempts': num_wrong + 1,
                    }
                    responses.append(resp)
                    if response == target:
                        progress += 1
                        prev_time = timestamp
                        num_wrong = 0
                        if target == "triggers":
                            done = True
                    else:
                        # If 3 incorrect buttons in a row, stop and show error
                        if self.trial_type == "PP":
                            total_errs += 1
                            num_wrong += 1
                            if num_wrong >= 3:
                                err = "repeat_err"
                        # If any button pressed during MI or CC, stop and show error
                        elif self.trial_type == "MI":
                            err = "mi_button"
                        elif self.trial_type == "CC":
                            err = "cc_button"
                        # End immediately if trial error encountered
                        if err != "NA":
                            done = True
                            break
                else:
                    # If trial timed out, stop and show error
                    if self.evm.after("timeout"):
                        err = "too_slow"
                        done = True
                        break

        # If MI/CC training trial and response is implausibly fast, show error
        if self.trial_type != "PP" and err == "NA":
            if (timestamp - start) < 1500:
                err = "too_fast"

        # Show RT feedback for 1.7 seconds, or error if trial timed out
        init_rt = responses[0]['rt'] if len(responses) else -1
        response_rt = -1
        if err == "NA":
            # Get response time
            response_rt = (timestamp - start)
            rt_sec = "{:.3f}".format(response_rt / 1000.0)
            # Get total error count
            if self.trial_type != "PP":
                err_str = "? Errors"
            elif total_errs < 2:
                err_str = "No Errors" if total_errs == 0 else "1 Error"
            else:
                err_str = "{0} Errors".format(total_errs)
            feedback = message(rt_sec + " / " + err_str, style='feedback')
            self.show_feedback(feedback, duration=1.7)
        else:
            feedback = self.errs[err]
            self.show_feedback(feedback, duration=2.5)
            # If sequence hasn't been shown yet, recycle trial
            if err == "too_soon":
                raise TrialException("recycle")

        # Log individual sequence elements/responses to database
        if len(responses):
            # On imagery/control trials, log sequence elements regardless 
            if self.trial_type != "PP":
                sequence = []
                for i in range(len(seq)):
                    element = {
                        'participant_id': P.participant_id,
                        'block_num': P.block_number,
                        'trial_num': P.trial_number,
                        'seq_name': self.seq_name,
                        'index': i + 1,
                        'element': seq[i],
                        'response': "NA",
                        'rt': -1,
                        'acc': True,
                        'n_attempts': 0,
                    }
                    sequence.append(element)
                responses = sequence + responses
            self.db.insert(responses, table='sequences')

        return {
            "block_num": P.block_number,
            "trial_num": P.trial_number,
            "trial_type": self.trial_type,
            "seq_type": self.seq_type,
            "seq_name": self.seq_name,
            "initial_rt": init_rt,
            "response_rt": response_rt,
            "total_errs": total_errs,
            "err": err,
        }


    def trial_clean_up(self):
        b1 = "{0}% complete!  ({1} / {2} trials)"
        b2 = "Take a break if you need one, then press any button to continue."
        # Show break messages at regular intervals
        break_interval = 15
        if P.trial_number % break_interval == 0:
            if P.trial_number == P.trials_per_block or self.block_label == "practice":
                return
            pct = int((P.trial_number / P.trials_per_block) * 100)
            self.show_demo_text(
                [b1.format(pct, P.trial_number, P.trials_per_block), b2], [],
                msg_y = int(P.screen_y * 0.45)
            )
            # Blank screen before returning to task to give time for button release
            fill()
            flip()
            wait_msec(500, self.gamepad)


    def clean_up(self):
        # Show message at end to indicate task is complete
        end_txt = (
            "You're all done, thanks for participating!\nPress any button to exit."
        )
        end_msg = message(end_txt, align='center')
        fill()
        blit(end_msg, 5, P.screen_c)
        flip()
        wait_for_input(self.gamepad)

        if self.gamepad:
            self.gamepad.close()


    def get_demo_stim(self):
        # Generate basic sequence stimuli
        stimset = {
            'fixation': [],
            'fix_diamond': [],
            'fix_star': [],
            'fix_plus': [],
            'seq': [],
            'seq_grey': [],
            'recall_cells': [],
            'arrows': [],
            'numbers': [],
            'pair': [],
        }
        demo_seq = ['2', '1', '3', 'Right', 'Up', 'Down', 'Left']
        i = 0
        for x_loc in get_x_locs(len(demo_seq)):
            loc = (int(P.screen_c[0] + self.item_offset * x_loc), P.screen_c[1])
            stimset['fixation'].append((self.fixations['circle'], loc))
            stimset['fix_diamond'].append((self.fixations['diamond'], loc))
            stimset['fix_star'].append((self.fixations['star'], loc))
            stimset['fix_plus'].append((self.fixations['plus'], loc))
            stimset['seq'].append((self.icons[demo_seq[i]], loc))
            stimset['seq_grey'].append((self.icons_grey[demo_seq[i]], loc))
            stimset['recall_cells'].append((self.cell, loc))
            i += 1
        # Generate stimuli for task intro
        arrows = ['Up', 'Down', 'Left', 'Right']
        numbers = ['1', '2', '3', '4']
        i = 0
        for x_loc in get_x_locs(len(arrows)):
            loc = (int(P.screen_c[0] + self.item_offset * x_loc), P.screen_c[1])
            stimset['arrows'].append((self.icons[arrows[i]], loc))
            stimset['numbers'].append((self.icons[numbers[i]], loc))
            i += 1
        pair = ['3', 'Down']
        i = 0
        for x_loc in get_x_locs(2):
            loc = (int(P.screen_c[0] + self.item_offset * x_loc), P.screen_c[1])
            stimset['pair'].append((self.icons[pair[i]], loc))
            i += 1
        bdist = self.icons["1"].shape[0]
        stimset['buttons'] = [
            (self.icons["1"], (P.screen_c[0] - bdist, P.screen_c[1])),
            (self.icons["2"], (P.screen_c[0], P.screen_c[1] - bdist)),
            (self.icons["3"], (P.screen_c[0] + bdist, P.screen_c[1])),
            (self.icons["4"], (P.screen_c[0], P.screen_c[1] + bdist)),
        ]
        # Generate additional stimuli
        stimset['seq_progress'] = stimset['seq'][:2] + stimset['seq_grey'][2:]
        stimset['seq_recall'] = stimset['seq'][:3]
        stimset['seq_recall2'] = stimset['seq'][:2]
        stimset['pair_err'] = [(message("XXXX", style="wrong"), P.screen_c)]
        feedback = message("4.234 / No Errors", style='feedback')
        stimset['feedback'] = [(feedback, P.screen_c)]
        return stimset


    def input_demo(self):
        # Pre-render the instructions and continue message
        instr1 = message(
            "To get a feel for the controls, try some inputs yourself!"
        )
        instr2 = message(
            "When you press a button or move the stick, its icon will appear below:"
        )
        next_msg = message(
            "When you're ready to continue, squeeze both rear triggers at once."
        )
        instr1_loc = (P.screen_c[0], int(P.screen_y * 0.25))
        instr2_loc = (P.screen_c[0], instr1_loc[1] + int(instr1.height * 1.5))
        next_loc = (P.screen_c[0], int(P.screen_y * 0.75))

        # Enter input demo loop until each input pressed at least once
        unique = set()
        resp_icon = None
        last_resp = 0
        done = False
        while not done:

            fill()
            blit(instr1, 8, instr1_loc)
            blit(instr2, 8, instr2_loc)
            since_resp = sdl2.SDL_GetTicks() - last_resp
            if last_resp != 0 and since_resp < 300:
                blit(resp_icon, 5, P.screen_c)
            if len(unique) == len(self.icons):
                blit(next_msg, 5, next_loc)
            flip()

            response, timestamp = self.get_sequence_input()
            if not response:
                continue
            else:
                if response == "triggers":
                    if len(unique) == len(self.icons):
                        done = True
                else:
                    last_resp = timestamp
                    resp_icon = self.icons[response]
                    unique.add(response)


    def pairs_practice(self):
        # Get all possible button pairs
        pairs = list(itertools.permutations(self.icons.keys(), r=2))
        shuffle(pairs)

        # Remind participants to squeeze triggers if they forget
        trig_msg = message(
            "Please squeeze the rear triggers to complete each sequence!"
        )

        # Iterate through pairs until all completed successfully
        pairs_err = message("XXXX", style="wrong")
        while len(pairs):
            progress = 0
            done_time = None
            seq = pairs.pop()
            stim = [self.icons_grey[e] for e in seq]

            fill()
            draw_sequence(stim, self.item_offset)
            flip()
            stim_onset = sdl2.SDL_GetTicks()

            while progress < 3:
                target = seq[progress] if progress < 2 else "triggers"
                response, timestamp = self.get_sequence_input()
                if not response:
                    if done_time and (sdl2.SDL_GetTicks() - done_time) > 3000:
                        self.show_feedback(trig_msg, duration=2.5)
                        break
                    else:
                        continue
                elif response == target:
                    progress += 1
                    if progress == 1:
                        stim[0] = self.icons[seq[0]]
                        fill()
                        draw_sequence(stim, self.item_offset)
                        flip()
                    elif progress == 2:
                        stim[1] = self.icons[seq[1]]
                        fill()
                        draw_sequence(stim, self.item_offset)
                        flip()
                        done_time = sdl2.SDL_GetTicks()
                    else:
                        fill()
                        flip()
                        wait_msec(500, self.gamepad)
                        # Make sure triggers released before next pair
                        while True:
                            if self.triggers_released():
                                break
                            self.show_feedback(
                                self.errs["start_triggers"], duration=0.5
                            )
                else:
                    self.show_feedback(pairs_err, duration=1.0)
                    pairs.append(seq)
                    break


    def run_seqence_recall(self):
        # Get order of last shapes from training block
        if len(self.seq_history):
            seqs_rev = reversed(self.seq_history)
            seq_order = [*dict.fromkeys(seqs_rev)]
            seq_order.reverse()
        else:
            seq_order = list(self.fixation_map.keys())

        # Run through instuctions and wait for input
        try:
            self.recall_instructions()
        except SkipInstructions:
            pass
        msg = message("When you're ready, press any key to start.")
        self.show_feedback(msg, duration=1.0)
        any_key()
        
        # Collect recall responses in sequential order
        for seq in seq_order:
            target_seq = P.sequences[seq]
            shape = self.fixation_map[seq]
            resp = self.sequence_recall(shape, len(target_seq))
            # Log response to database
            sequence = []
            for i in range(len(target_seq)):
                element = {
                    'participant_id': P.participant_id,
                    'seq_order': seq_order.index(seq) + 1,
                    'seq_name': seq,
                    'shape': shape,
                    'index': i + 1,
                    'element': target_seq[i],
                    'response': resp[i]['item'],
                    'rt': resp[i]['rt'],
                    'acc': resp[i]['item'] == target_seq[i],
                }
                sequence.append(element)
            self.db.insert(sequence, table='recall')

        # Wait for participant to pick up controller and press a button
        msg = message(
            ("Recall phase complete!\n\nPlease pick up the controller and press any "
            "button to continue."), align='center'
        )
        self.show_feedback(msg, duration=1.0)
        button = False
        while not button:
            if self.gamepad:
                self.gamepad.update()
            q = pump()
            ui_request(queue=q)
            button = len(get_buttons(q))


    def sequence_recall(self, shape, seq_len):
        # Generate prompt message and get sequence item locations
        shape_plural = shape + "ses" if shape == "plus" else shape + "s"
        prompt = (
            "Please enter the sequence that followed the *{0}* to the best of\n"
            "your memory, using the number and arrow keys:"
        )
        msg = message(prompt.format(shape_plural), align='center')
        x_locs = get_x_locs(seq_len)

        # Start input loop and collect recall response
        start = sdl2.SDL_GetTicks()
        resp = []
        done = False
        while not done:
            # Check for keyboard input
            q = pump()
            ui_request(queue=q)
            for k, timestamp in get_keys(q):
                if k == "Backspace":
                    resp = resp[:-1]
                elif k in ("Return", "Enter"):
                    if len(resp) == seq_len:
                        done = True
                        break
                elif k in self.icons.keys():
                    prev = resp[-1]['timestamp'] if len(resp) else start
                    if len(resp) < seq_len:
                        rt = timestamp - prev
                        resp += [{'item': k, 'timestamp': timestamp, 'rt': rt}]

            # Draw the screen and current progress
            fill()
            blit(msg, 5, (P.screen_c[0], int(P.screen_y * 0.2)))
            for i in range(seq_len):
                loc_x = int(P.screen_c[0] + self.item_offset * x_locs[i])
                loc_y = int(P.screen_y * 0.5)
                blit(self.fixations[shape], 5, (loc_x, int(P.screen_y * 0.38)))
                blit(self.cell, 5, (loc_x, loc_y))
                if i < len(resp):
                    blit(self.icons[resp[i]['item']], 5, (loc_x, loc_y))
            flip()

        return resp


    def get_sequence_input(self):

        # Refresh input from all sources
        if self.gamepad:
            self.gamepad.update()
        q = pump()
        ui_request(queue=q)
        buttons = get_buttons(q)
        stick_movement = self.get_stick_movement()
        
        response = None
        timestamp = None

        if len(buttons):
            # Handle controller button input
            b = buttons[0]
            if b.name in self.buttonmap.keys():
                response = self.buttonmap[b.name]
                timestamp = b.timestamp
        elif stick_movement:
            # Handle stick movement input
            response = stick_movement
            timestamp = sdl2.SDL_GetTicks()
        else:
            # Handle trigger input
            lt, rt = self.get_triggers()
            if lt > 0.5 and rt > 0.5:
                if not self._triggers_down:
                    response = "triggers"
                    timestamp = sdl2.SDL_GetTicks()
                    self._triggers_down = True
            else:
                self._triggers_down = False

        return (response, timestamp)


    def show_feedback(self, msg, duration=1.0, location=None):
        feedback_time = CountDown(duration)
        if not location:
            location = P.screen_c
        while feedback_time.counting():
            ui_request()
            if self.gamepad:
                self.gamepad.update()
            fill()
            blit(msg, 5, location)
            flip()


    def triggers_released(self):
        if self.gamepad:
            self.gamepad.update()
        lt, rt = self.get_triggers()
        return lt < 0.5 and rt < 0.5


    def show_demo_text(self, msgs, stim_set, duration=2.0, wait=True, msg_y=None):
        msg_x = int(P.screen_x / 2)
        msg_y = int(P.screen_y * 0.25) if msg_y is None else msg_y
        half_space = deg_to_px(0.5)

        fill()
        if not isinstance(msgs, list):
            msgs = [msgs]
        for msg in msgs:
            txt = message(msg, align="center")
            blit(txt, 8, (msg_x, msg_y))
            msg_y += txt.height + half_space
    
        for x in stim_set:
            # If background stimulus has blit() method, use that to draw it
            if hasattr(x, 'blit'):
                x.blit()
            else:
                stim, locs = x
                if not isinstance(locs, list):
                    locs = [locs]
                for loc in locs:
                    blit(stim, 5, loc)
        flip()
        if P.development_mode and wait:
            wait_msec(500)
        else:
            wait_msec(duration * 1000)
        if wait:
            wait_for_input(self.gamepad, demo=True)


    def get_stick_movement(self, from_center=True):
        state = None
        movement = None
        direction = get_stick_direction(self.gamepad)
        if direction in self.stick_map.keys():
            state = self.stick_map[direction]
        if state != None and direction != self._stick_prev_direction:
            if not (from_center and self._stick_prev_direction != 0):
                movement = state
        self._stick_prev_direction = direction
        return movement


    def get_triggers(self):
        if self.gamepad:
            raw_lt = self.gamepad.left_trigger()
            raw_rt = self.gamepad.right_trigger()
        else:
            # If no gamepad, emulate trigger press with spacebar press
            raw_lt, raw_rt = (0, 0)
            if get_key_state('space') != 0:
                raw_lt, raw_rt = (32767, 32767)

        return (raw_lt / TRIGGER_MAX, raw_rt / TRIGGER_MAX)



class SkipInstructions(Exception):
    # Dummy exception for making it easy to skip instructions
    pass


class ProgressMessage():

    def __init__(self, fmt, total, loc=None, reg=8, textstyle='default', autotick=False):
        self.total = total
        self.progress = 0
        self.autotick = autotick

        self.fmt = fmt
        self.loc = loc if loc else (P.screen_c[0], int(P.screen_y * 0.05))
        self.reg = reg
        self.fstyle = textstyle

    def tick(self):
        if self.progress < self.total:
            self.progress += 1
    
    @property
    def done(self):
        return self.progress >= self.total

    def blit(self):
        if self.autotick:
            self.tick()
        txt = self.fmt.format(self.progress, self.total)
        msg = message(txt, style=self.fstyle)
        blit(msg, self.reg, self.loc)


def joystick_scaled(x, y, deadzone = 0.2):

    # Check whether the current stick x/y exceeds the specified deadzone
    amplitude = min(1.0, sqrt(x ** 2 + y ** 2) / AXIS_MAX)
    if amplitude < deadzone:
        return (0, 0)

    # Smooth/standardize output coordinates to be on a circle, by capping
    # maximum amplitude at AXIS_MAX and converting stick angle/amplitude
    # to coordinates.
    angle = angle_between((0, 0), (x, y))
    amp_new = (amplitude - deadzone) / (1.0 - deadzone)
    xs, ys = point_pos((0, 0), amp_new, angle, return_int=False)

    return (xs, ys)


def get_stick_position(gamepad, left=True):
    if gamepad:
        if left:
            raw_x, raw_y = gamepad.left_stick()
        else:
            raw_x, raw_y = gamepad.right_stick()
    else:
        # If no gamepad, approximate joystick with mouse movement
        mouse_x, mouse_y = mouse_pos()
        scale_factor = AXIS_MAX / (P.screen_y / 2)
        raw_x = int((mouse_x - P.screen_c[0]) * scale_factor)
        raw_y = int((mouse_y - P.screen_c[1]) * scale_factor)

    return joystick_scaled(raw_x, raw_y)


def get_stick_direction(gamepad, left=True, threshold = 0.8):
    # Converts stick direction to an integer between 1 and 8, depending on the
    # quadrant of movement (0 = no stick movement)
    x, y = get_stick_position(gamepad, left=left)
    amplitude = sqrt(x ** 2 + y ** 2)
    if amplitude > threshold:
        # Split into 8 quadrants with up/down/left/right having 70° ranges 
        # with 20° buffer zones in between
        angle = angle_between((0, 0), (x, y), rotation=-125, clockwise=True)
        zone = int(angle / 90.0)
        offset = 1 if (angle % 90 > 70) else 0
        return (zone * 2) + offset + 1
    return 0


def wait_msec(duration, gamepad=None):
    start = sdl2.SDL_GetTicks()
    while (sdl2.SDL_GetTicks() - start) < duration:
        if gamepad:
            gamepad.update()
        ui_request()

    
def wait_for_input(gamepad=None, demo=False):
    # Waits until mouse button, key, or controller button pressed 
    valid_input = [
        sdl2.SDL_KEYDOWN,
        sdl2.SDL_MOUSEBUTTONDOWN,
        sdl2.SDL_CONTROLLERBUTTONDOWN,
    ]
    flush()
    user_input = False
    while not user_input:
        if gamepad:
            gamepad.update()
        q = pump(True)
        ui_request(queue=q)
        for event in q:
            if event.type in valid_input:
                keydown = event.type == sdl2.SDL_KEYDOWN
                if keydown:
                    if event.key.repeat:
                        continue
                    elif demo and event.key.keysym.sym == sdl2.SDLK_ESCAPE:
                        if P.development_mode:
                            raise SkipInstructions
                user_input = True
                break


def get_buttons(events):
    # Get button events and/or keyboard-simulated button events
    buttons = []
    for e in events:
        # Handle actual controller button events
        if e.type == sdl2.SDL_CONTROLLERBUTTONDOWN:
            buttons.append(ControllerButton(e))
        # Handle keypress-simulated button events
        elif P.development_mode and e.type == sdl2.SDL_KEYDOWN:
            if e.key.repeat:
                continue
            keyname = sdl2.SDL_GetKeyName(e.key.keysym.sym).decode('utf-8')
            if keyname.lower() in P.button_keymap.keys():
                bname = P.button_keymap[keyname.lower()]
                buttons.append(VirtualButton(bname, e.key.timestamp))
    return buttons


def get_keys(events):
    # Get keypress events
    keys = []
    for e in events:
        if e.type == sdl2.SDL_KEYDOWN:
            if e.key.repeat:
                continue
            key = sdl2.SDL_GetKeyName(e.key.keysym.sym).decode('utf-8')
            if "Keypad" in key:
                key = key.replace("Keypad ", "")
            keys.append((key, e.key.timestamp))
    return keys


def random_choices(x, n=1):
	# Make random choices from a list, ensuring all elements from x are chosen
	# at least once if n >= len(x)
	out = x.copy()
	shuffle(out)
	while len(out) < n:
		more = x.copy()
		shuffle(more)
		out += more
	return out[:n]


def random_choices2(x, n=1):
    # Make random choices from a list, ensuring no immediate repeats
    items = x.copy()
    out = []
    last = None
    while len(out) < n:
        shuffle(items)
        i = 0 if items[0] != last else 1
        out.append(items[i])
        last = items[i]
    return out


def get_x_locs(seq_len):
    # Gets the x-axis offsets for a sequence of a given length
    offset = (seq_len - 1) / 2
    return [i - offset for i in range(seq_len)]


def draw_sequence(elements, spacing, count=None):
    if not count:
        count = len(elements)
    # If count exceeds number of elements, duplicate 1st element
    if count > len(elements):
        elements = [elements[0]] * count
    # Actually draw the sequence elements
    x_locs = get_x_locs(count)
    for i in range(count):
        loc = (int(P.screen_c[0] + spacing * x_locs[i]), P.screen_c[1])
        blit(elements[i], 5, loc)


def draw_button(diameter, text, color):
    circle = kld.Ellipse(diameter, fill=color).render()
    bstyle = TextStyle(size="{0}px".format(int(diameter * 0.65)))
    txt = message(text, style=bstyle)
    txt.trim()
    nps = NumpySurface(circle)
    nps.blit(txt, 5, nps.surface_c)
    return nps.render()
