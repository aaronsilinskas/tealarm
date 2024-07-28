import time
from .observers import Observers


class State:
    @property
    def name(self):
        return type(self).__name__

    def enter(self, thing: "Thing"):
        pass

    def exit(self, thing: "Thing"):
        pass

    def update(self, thing: "Thing") -> "State":
        return self


class ThingObserver:
    def state_changed(self, old_state: State, new_state: State):
        pass


class Thing:

    def __init__(self, initial_state: State):
        assert initial_state, "initial_state is required"

        self.__observers = Observers()
        self.__initial_state = initial_state

        self.__current_state: State = None
        self.__previous_state: State = None
        self.__time_last_update: float = 0
        self.__time_ellapsed: float = 0
        self.__time_active: float = 0

    def go_to_state(self, state: State):
        assert state, "state can not be None"

        if self.__current_state == state:
            return

        if self.__current_state:
            self.__current_state.exit(self)

        self.__previous_state = self.__current_state
        self.__current_state = state

        if self.__previous_state:
            self.observers.notify(
                "state_changed", self.__previous_state, self.__current_state
            )

        self.__time_last_update = time.monotonic()
        self.__time_ellapsed = 0
        self.__time_active = 0
        self.__current_state.enter(self)

    def update(self):
        if self.__current_state is None:
            self.go_to_state(self.__initial_state)
            
        now = time.monotonic()
        self.__time_ellapsed = now - self.__time_last_update
        self.__time_last_update = now
        self.__time_active += self.__time_ellapsed

        next_state = self.__current_state.update(self)
        if next_state != self.__current_state:
            self.go_to_state(next_state)

    @property
    def current_state(self) -> State:
        return self.__current_state

    @property
    def previous_state(self) -> State:
        return self.__previous_state

    @property
    def time_ellapsed(self) -> float:
        return self.__time_ellapsed

    @property
    def time_active(self) -> float:
        return self.__time_active

    @property
    def observers(self) -> Observers:
        return self.__observers
