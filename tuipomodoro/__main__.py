from tuipomodoro.app import PomodoroTimerApp
from tuipomodoro.timer import PomodoroTimer


def main():
    timer = PomodoroTimer()
    app = PomodoroTimerApp(timer)
    app.run()


if __name__ == "__main__":
    main()
