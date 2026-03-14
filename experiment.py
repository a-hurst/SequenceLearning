# -*- coding: utf-8 -*-

__author__ = "Austin Hurst"

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
from klibs.KLUserInterface import (
    any_key, mouse_pos, ui_request, hide_cursor, smart_sleep,
)
from sdl2.ext import get_key_state

from gamepad import gamepad_init, button_pressed, ControllerButton, VirtualButton
from gamepad_usb import get_all_controllers
from picodraw import draw_arrow, draw_circle, draw_square, draw_star, draw_asterisk


# Define colours for use in the experiment
WHITE = (255, 255, 255)
LIGHT_GREY = (192, 192, 192)
BLACK = (0, 0, 0)
MIDGREY = (128, 128, 128)
TRANSLUCENT_RED = (255, 0, 0, 96)
TRANSLUCENT_BLUE = (0, 0, 255, 96)
NICE_RED = (224, 121, 110)
NICE_GREEN = (82, 182, 75)

IBM_PALETTE = [
    (128, 163, 248),
    (137, 122, 235),
    (211, 79, 143),
    (238, 127, 49),
    (245, 192, 46),
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
        self.block_msg_loc = (P.screen_c[0], int(P.screen_y * 0.4))
        self.lower_middle = (P.screen_c[0], int(P.screen_y * 0.75))

        # Initialize custom text styles
        add_text_style("wrong", size='1.0deg', color=NICE_RED)
        add_text_style("feedback", size='0.7deg')

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
            "dpup": "Up",
            "dpdown": "Down",
            "dpleft": "Left",
            "dpright": "Right",
            "y": "1",
            "x": "2",
            "a": "3",
            "b": "4",
        }

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
            "1": draw_button(item_w, "1", color=IBM_PALETTE[0]),
            "2": draw_button(item_w, "2", color=IBM_PALETTE[1]),
            "3": draw_button(item_w, "3", color=IBM_PALETTE[2]),
            "4": draw_button(item_w, "4", color=IBM_PALETTE[3]),
        }
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
            "too_slow": "Too slow!\nPlease try to respond faster.",
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
        self._triggers_down = False

        # Create fixation map for training block
        training_fixations = ['diamond', 'star', 'plus']
        self.fixation_map = {}
        for seq in self.practiced_seqs:
            self.fixation_map[seq] = training_fixations.pop()

    
    def get_demo_stim(self):
        # Generate basic sequence stimuli
        stimset = {
            'fixation': [],
            'fix_diamond': [],
            'fix_star': [],
            'fix_plus': [],
            'seq': [],
            'seq_grey': [],
        }
        demo_seq = ['2', '1', '3', 'Right', 'Up', 'Down', 'Left']
        i = 0
        for x_loc in [-3, -2, -1, 0, 1, 2, 3]:
            loc = (int(P.screen_c[0] + self.item_offset * x_loc), P.screen_c[1])
            stimset['fixation'].append((self.fixations['circle'], loc))
            stimset['fix_diamond'].append((self.fixations['diamond'], loc))
            stimset['fix_star'].append((self.fixations['star'], loc))
            stimset['fix_plus'].append((self.fixations['plus'], loc))
            stimset['seq'].append((self.icons[demo_seq[i]], loc))
            stimset['seq_grey'].append((self.icons_grey[demo_seq[i]], loc))
            i += 1
        # Generate additional stimuli
        stimset['seq_progress'] = stimset['seq'][:2] + stimset['seq_grey'][2:]
        feedback = message("4.234 / No Errors", style='feedback')
        stimset['feedback'] = [(feedback, P.screen_c)]
        return stimset


    def practice_instructions(self):
        stim = self.get_demo_stim()
        self.show_demo_text(
            ("Now that you have some practice with the controls, let's try some "
             "full sequences!"),
            stim['fixation'],
        )
        self.show_demo_text(
            ("Each trial starts with a row of shapes, showing you where the sequence "
             "is about to appear:"),
            stim['fixation'],
        )
        self.show_demo_text(
            ("When the sequence appears, your job will be to try to quickly perform "
             "the sequence of\nmovements yourself using the joystick and buttons on "
             "the game controller."),
            stim['seq_grey'],
        )
        self.show_demo_text(
            ("As you press each item in the sequence its icon will light up, letting "
             "you know\nyou made the correct response and showing your progress."),
            stim['seq_progress'],
        )
        self.show_demo_text(
            ("Once you have responded to all items in the sequence, squeeze both "
             "triggers at once\non the back of the controller to end the trial."),
            stim['seq'],
        )
        self.show_demo_text(
            ("At the end of each trial, you will be given feedback on your speed and "
             "accuracy.\nPlease try to complete the sequences as quickly as you can "
             "without making mistakes!"),
            stim['feedback'],
        )

    def training_instructions(self):
        stim = self.get_demo_stim()
        self.show_demo_text(
            ("Now that you've gotten some practice, in this next phase of the study "
             "you will train on\n3 sequences repeatedly to see how much you can "
             "improve your performance!"),
            stim['fixation'],
        )

        if P.condition == "MI":
            self.training_instructions_mi()
        elif P.condition == "CC":
            self.training_instructions_cc()

        self.show_demo_text(
            ("In this training block, each of the three sequences will start with a "
             "different row of shapes.\nOne sequence will start with diamonds:"),
            stim['fix_diamond'],
        )
        self.show_demo_text(
            "Another sequence will start with stars:",
            stim['fix_star'],
        )
        self.show_demo_text(
            "And the third sequence will start with plus signs:",
            stim['fix_plus'],
        )
        self.show_demo_text(
            ("You can use these shapes to help prepare for each sequence before "
             "it appears!"),
            stim['fix_plus'],
        )
        self.show_demo_text(
            ("At the end of the study, you will be tested on how quickly and "
             "accurately you can\nperform each of the three sequences."),
            stim['seq_grey'],
        )
        self.show_demo_text(
            ("Because this is a *training* phase, your goal is to practice the "
             "sequences in order\nto perform as well as you can in the final "
             "test block."),
            stim['seq_grey'],
        )
        self.show_demo_text(
            ("Note that this does not necessarily mean practicing as quickly as "
             "possible: if you think\nit would help more to go slowly and think things "
             "through, take your time!"),
            stim['seq_grey'],
        )

    def training_instructions_mi(self):
        stim = self.get_demo_stim()
        self.show_demo_text(
            ("During this block, instead of performing sequences of movements "
             "*physically* you will\ninstead be asked to rehearse the sequences "
             "*mentally* using motor imagery."),
            stim['seq_grey'],
        )
        self.show_demo_text(
            ("This means that instead of physically pressing buttons or moving the "
             "joystick, try to\nsimply *imagine* the movements you would need to make "
             "for each sequence."),
            stim['seq_grey'],
        )
        self.show_demo_text(
            ("For example, you might visualize how your right thumb would move "
             "between the 2, 1,\n& 3 buttons, then imagine using your left thumb to "
             "move the stick right, up, down, & left."),
            stim['seq_grey'],
        )
        self.show_demo_text(
            ("If it helps, you can try to visualize the icons lighting up and simulate "
             "how each movement\nwould *feel* as you move through the sequence in "
             "your mind."),
            stim['seq_grey'],
        )
        self.show_demo_text(
            ("Please try to avoid actually moving your hands and keep your thumbs "
             "relaxed\nas you imagine performing the movements."),
            stim['seq_grey'],
        )
        self.show_demo_text(
            ("Once you have completed the sequence in your mind, please squeeze the "
             "rear\ntriggers *physically* to end the trial."),
            stim['seq_grey'],
        )

    def training_instructions_cc(self):
        stim = self.get_demo_stim()
        self.show_demo_text(
            ("During this block, instead of performing sequences of movements "
             "*physically* you will\ninstead be asked to rehearse the sequences "
             "*mentally* by repeating them silently in your head."),
            stim['seq_grey'],
        )
        self.show_demo_text(
            ("For example, you would practice the sequence below by repeating "
            "“two, one, three, right,\nup, down, left” to yourself silently, and "
            "then squeezing the triggers to end the trial."),
            stim['seq_grey'],
        )
        self.show_demo_text(
            ("Please try and keep your hands still and avoid actual movement during "
             "mental rehearsal.\nSimply focus on rehearsing the names of the symbols "
             "in each sequence."),
            stim['seq_grey'],
        )

    def test_instructions(self):
        stim = self.get_demo_stim()
        self.show_demo_text(
            ("Welcome to the final phase of the experiment! In this section, you "
             "will be tested on\nhow quickly and accurately you can perform the "
             "sequences you practiced."),
            stim['fixation'],
        )
        self.show_demo_text(
            ("For this phase, please perform the sequences physically using the game "
             "controller.\nYou will receive feedback on your accuracy and response "
             "times."),
            stim['seq_grey'],
        )
        self.show_demo_text(
            ("Note that this block contains 6 different sequences: the 3 you practiced "
             "during the training\nphase as well as 3 unpracticed sequences. Try your "
             "best to perform well on all of them!"),
            stim['seq_grey'],
        )
        self.show_demo_text(
            "In this block, the starting row of shapes is the same for all sequences.",
            stim['fixation'],
        )
        self.show_demo_text(
            ("At the end of each trial, you will be given feedback on your speed and "
             "accuracy.\nPlease try to complete the sequences as quickly as you can "
             "without making mistakes!"),
            stim['feedback'],
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

        # Show block instructions
        if self.block_label == "practice":
            self.practice_instructions()
        if self.block_label == "training":
            self.training_instructions()
            block_msg = block_msgs["training_" + P.condition]
        elif self.block_label == "test":
            self.test_instructions()
        
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
        self.evm.add_event('sequence_on', onset=800)
        self.evm.add_event('timeout', onset=15000, after='sequence_on')

        # Reset input state
        self._triggers_down = False
        self._stick_prev_direction = 0

        # Ensure triggers released prior to trial start
        while True:
            lt, rt = self.get_triggers()
            if lt < 0.5 and rt < 0.5:
                break
            self.show_feedback(self.errs["start_triggers"], duration=0.5)


    def trial(self):

        # Need to decide circumstances resulting in a trial error
        #   - Timeout seems reasonable, but needs to be long to account for slow MI
        #   - Pre-sequence response?
        # For CC/MI, start progress at 7 with all elements lit?

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
            if self.trial_type == "PP" and progress < 7:
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
            if total_errs < 2:
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
    
        for stim, locs in stim_set:
            if not isinstance(locs, list):
                locs = [locs]
            for loc in locs:
                blit(stim, 5, loc)
        flip()
        if P.development_mode and wait:
            smart_sleep(500)
        else:
            smart_sleep(duration * 1000)
        if wait:
            wait_for_input(self.gamepad)


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
        angle = angle_between((0, 0), (x, y), rotation=-112.5, clockwise=True)
        return int(angle / 45.0) + 1
    return 0

    
def wait_for_input(gamepad=None):
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
                if keydown and event.key.repeat:
                    continue
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
            keys.append(key)
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


def draw_sequence(elements, spacing, count=None):
    if not count:
        count = len(elements)
    # If count exceeds number of elements, duplicate 1st element
    if count > len(elements):
        elements = [elements[0]] * count
    # Calculate offsets for sequence count
    offset = (count - 1) / 2
    x_locs = [i - offset for i in range(count)]
    # Actually draw the sequence elements
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
