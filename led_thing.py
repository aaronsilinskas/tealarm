from pwmio import PWMOut
from state_of_things import State, Thing


class LEDThing(Thing):
    def __init__(self, led_pwm: PWMOut):
        super().__init__(LEDStates.off)

        self.led_pwm: PWMOut = led_pwm

        self.brightness_target: float = 0
        self.brightness_start: float = 0
        self.time_lighting: float = 0
        self.time_dimming: float = 0

    @property
    def brightness(self) -> float:
        return round(self.led_pwm.duty_cycle / 65536, 2)

    @brightness.setter
    def brightness(self, value: float):
        new_duty_cycle = max(0, min(int(65535 * value), 65535))
        if self.led_pwm.duty_cycle != new_duty_cycle:
            self.led_pwm.duty_cycle = new_duty_cycle
            # self.__log(f"Brightness: {value}")

    def turn_off(self, time_dimming: float = 0):
        self.brightness_start = self.brightness
        self.brightness_target = 0
        self.time_lighting = 0
        self.time_dimming = time_dimming
        self.go_to_state(LEDStates.off)

    def turn_on(self, time_lighting: float = 0):
        self.brightness_start = self.brightness
        self.brightness_target = 1.0
        self.time_lighting = time_lighting
        self.time_dimming = 0
        self.go_to_state(LEDStates.lighting)

    def adjust(self, brightness_target: float, time_transition: float = 0):
        self.brightness_start = self.brightness
        self.brightness_target = brightness_target
        if brightness_target < self.brightness_start:
            self.time_dimming = time_transition
            self.time_lighting = 0
            self.go_to_state(LEDStates.dimming)
        else:
            self.time_dimming = 0
            self.time_lighting = time_transition
            self.go_to_state(LEDStates.lighting)

    def blink(self, brightness_target: float, time_lighting: float, time_dimming: float):
        self.brightness_start = self.brightness
        self.brightness_target = brightness_target
        self.time_lighting = time_lighting
        self.time_dimming = time_dimming

        self.go_to_state(LEDStates.lighting)


class LEDStates:
    waiting: State
    off: State
    lighting: State
    dimming: State
    on: State


class OffState(State):
    def update(self, thing: LEDThing):
        if thing.brightness > 0:
            thing.brightness = 0

        return self


LEDStates.off = OffState()


class OnState(State):

    def update(self, thing: LEDThing):
        if thing.brightness != thing.brightness_target:
            thing.brightness = thing.brightness_target

        return self


LEDStates.on = OnState()


class LightingState(State):

    def update(self, thing: LEDThing):
        if thing.time_active >= thing.time_lighting:
            thing.brightness = thing.brightness_target
            thing.time_lighting = 0
            if thing.time_dimming > 0:
                thing.brightness_start = thing.brightness_target
                thing.brightness_target = 0
                return LEDStates.dimming
            else:
                return LEDStates.on

        transition_percent = thing.time_active / thing.time_lighting
        thing.brightness = thing.brightness_start + (thing.brightness_target - thing.brightness_start) * transition_percent
        return self


LEDStates.lighting = LightingState()


class DimmingState(State):
    def update(self, thing: LEDThing):
        if thing.time_active >= thing.time_dimming:
            thing.brightness = thing.brightness_target
            thing.time_dimming = 0
            if thing.brightness_target > 0:
                return LEDStates.on
            else:
                return LEDStates.off

        transition_percent = thing.time_active / thing.time_dimming
        thing.brightness = thing.brightness_start + (thing.brightness_target - thing.brightness_start) * transition_percent
        return self


LEDStates.dimming = DimmingState()
