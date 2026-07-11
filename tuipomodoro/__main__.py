from tuipomodoro.app import PomodoroTimerApp
from tuipomodoro.config import Settings
from tuipomodoro.timer import PomodoroTimer


def main():
    settings = Settings.load()
    timer = PomodoroTimer(settings.timer_duration)
    app = PomodoroTimerApp(timer, settings)
    app.run()


if __name__ == "__main__":
    main()
