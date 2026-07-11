from tuipomodoro.app import PomodoroTimerApp
from tuipomodoro.config import Settings
from tuipomodoro.timer import CycleManager


def main():
    settings = Settings.load()
    manager = CycleManager(settings)
    app = PomodoroTimerApp(manager, settings)
    app.run()


if __name__ == "__main__":
    main()
