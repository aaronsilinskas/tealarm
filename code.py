"""
Don't Forget Your Tea!
Uses an FSR (Force Sensitive Resistor) to monitor how long tea/coffee has been sitting on it.
If it has sit too long, begin an alarm sequence.
"""

import time
import board
from pwmio import PWMOut
from analogio import AnalogIn
import busio
from adafruit_debouncer import Debouncer
from adafruit_ticks import ticks_ms
from state_of_things import State, Thing, ThingObserver
from led_thing import LEDThing
from mindwidgets_df1201s import DF1201S

# CONFIGURATION

# Sound length in seconds
SOUND_LENGTH = 30
SOUND_FILENAME = "/ffsong.wav"
VOLUME_ALARM = 0.2

# Pressure for cup detection (0 to 1)
PRESSURE_DEBOUNCE = 0.5
PRESSURE_THRESHOLD = 0.81

# Times in seconds
STARTUP_TIME = 2
BLINK_ON_TIME = 0.5
BLINK_OFF_TIME = 0.25
BLINK_TIME = BLINK_ON_TIME + BLINK_OFF_TIME
BREW_TIME = 9 * 60
DRINK_TIME = BREW_TIME / 2
CUP_GONE_TIME = 60
SILENT_ALARM_TIME = 60
SOUND_ALARM_TIME = SOUND_LENGTH
ALARM_BREAK_TIME = SOUND_LENGTH / 2

# LED
BRIGHTNESS_WAITING = 0.05
BRIGHTNESS_CUP_DETECTED = 0.1

# HARDWARE INITIALIZATION

# LED
led_pwm = PWMOut(board.D13, frequency=500)

# Force Sensor
fsr = AnalogIn(board.A0)
fsr_debouncer = Debouncer(lambda: fsr.value / 65535 > PRESSURE_THRESHOLD, PRESSURE_DEBOUNCE)

# Sound
uart = busio.UART(tx=board.TX, rx=board.RX, baudrate=115200)

df_player = DF1201S(uart)
df_player.volume = 0
df_player.disable_led()
df_player.disable_prompt()
df_player.enable_amp()
df_player.play_mode = DF1201S.PLAYMODE_PLAY_ONCE

# TEALARM THING

class TealarmThing(Thing):
    def __init__(self, led: LEDThing, pressure_debouncer: Debouncer):
        super().__init__(TealarmStates.startup)

        self.led = led
        self._pressure_debouncer = pressure_debouncer

        self.set_volume(0)

    def set_volume(self, level):
        df_player.volume = level

    @property
    def pressure_detected(self):
        return self._pressure_debouncer.value

    def play_sound(self, filename, volume):
        self.set_volume(volume)
        df_player.play_file_name(filename)

    def stop_sound(self):
        # TODO need a pause command in driver
        df_player.volume = 0


class TealarmStates:
    startup: State
    waiting: State
    cup_detected: State
    brewing: State
    drinking: State
    cup_lifted: State
    silent_alarm: State
    sound_alarm: State
    alarm_break: State


class Startup(State):
    def enter(self, thing: TealarmThing):
        thing.led.blink(
            brightness_target=0.5, time_lighting=STARTUP_TIME / 2, time_dimming=STARTUP_TIME / 2)

    def update(self, thing: TealarmThing):
        if thing.time_active >= STARTUP_TIME:
            return TealarmStates.waiting

        return self


TealarmStates.startup = Startup()


class Waiting(State):

    def enter(self, thing: TealarmThing):
        thing.led.adjust(BRIGHTNESS_WAITING, time_transition=BLINK_ON_TIME)
        thing.stop_sound()

    def update(self, thing: TealarmThing):
        if thing.pressure_detected:
            return TealarmStates.cup_detected

        return self


TealarmStates.waiting = Waiting()


class CupDetected(State):

    def enter(self, thing: TealarmThing):
        thing.led.blink(
            brightness_target=1, time_lighting=BLINK_ON_TIME, time_dimming=BLINK_OFF_TIME)

    def update(self, thing: TealarmThing):        
        return TealarmStates.brewing


TealarmStates.cup_detected = CupDetected()


class Brewing(State):

    def enter(self, thing: TealarmThing):
        thing.led.adjust(BRIGHTNESS_CUP_DETECTED, time_transition=BLINK_ON_TIME)

    def update(self, thing: TealarmThing):
        if not thing.pressure_detected:
            return TealarmStates.cup_lifted
        if thing.time_active > BREW_TIME:
            return TealarmStates.silent_alarm
        return self


TealarmStates.brewing = Brewing()

class Drinking(State):

    def enter(self, thing: TealarmThing):
        thing.led.adjust(BRIGHTNESS_CUP_DETECTED, time_transition=BLINK_ON_TIME)

    def update(self, thing: TealarmThing):
        if not thing.pressure_detected:
            return TealarmStates.cup_lifted

        if thing.time_active > DRINK_TIME:
            return TealarmStates.silent_alarm

        return self

TealarmStates.drinking = Drinking()

class CupLifted(State):

    def enter(self, thing: TealarmThing):
        thing.led.adjust(BRIGHTNESS_WAITING, time_transition=BLINK_ON_TIME)
        thing.stop_sound()

    def update(self, thing: TealarmThing):
        if thing.pressure_detected:
            return TealarmStates.drinking

        if thing.time_active > CUP_GONE_TIME:
            return TealarmStates.waiting
        
        return self

TealarmStates.cup_lifted = CupLifted()

class SilentAlarm(State):

    def enter(self, thing: TealarmThing):
        thing.led.turn_on(time_lighting=SILENT_ALARM_TIME)

    def update(self, thing: TealarmThing):
        if not thing.pressure_detected:
            return TealarmStates.cup_lifted

        if thing.time_active > SILENT_ALARM_TIME:
            return TealarmStates.sound_alarm

        return self


TealarmStates.silent_alarm = SilentAlarm()


class SoundAlarm(State):

    def enter(self, thing: TealarmThing):
        thing.play_sound(SOUND_FILENAME, VOLUME_ALARM)

    def update(self, thing: TealarmThing):
        if not thing.pressure_detected:
            return TealarmStates.cup_lifted

        if thing.time_active > SOUND_ALARM_TIME:
            return TealarmStates.alarm_break

        # TODO increase volume over time

        return self


TealarmStates.sound_alarm = SoundAlarm()


class AlarmBreak(State):

    def enter(self, thing: TealarmThing):
        thing.stop_sound()

    def update(self, thing: TealarmThing):
        if not thing.pressure_detected:
            return TealarmStates.cup_lifted

        if thing.time_active > ALARM_BREAK_TIME:
            return TealarmStates.sound_alarm

        return self


TealarmStates.alarm_break = AlarmBreak()

class StateLoggerObserver(ThingObserver):
    def state_changed(self, old_state: State, new_state: State):
        print(f"State change from {old_state.name} to {new_state.name}")
        
led = LEDThing(led_pwm)
tealarm = TealarmThing(led, fsr_debouncer)
tealarm.observers.attach(StateLoggerObserver())

while True:
    fsr_debouncer.update()
    tealarm.update()
    led.update()

    # print(fsr.value / 65535)

    time.sleep(0.01)
