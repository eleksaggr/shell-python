import curses
from curses import cbreak, echo, endwin, initscr, nocbreak, noecho
import logging
from os import environ
from subprocess import check_output, CalledProcessError
from time import sleep
from threading import Thread
from queue import Queue


class Job(Thread):
    __nextId = 0

    def __init__(self, shell, command):
        super(Job, self).__init__()
        self.id = Job.__nextId
        Job.__nextId += 1

        self.__shell = shell
        self.__command = command
        self.result = ""

    def run(self):
        try:
            self.result = check_output(self.__shell.history.last().split())
            logging.info("Job {0} has ended.".format(self.id))
            self.__shell.writer.add(self.result.decode("utf-8"))
        except FileNotFoundError as e:
            self.__shell.writer.add("{0}\n".format(str(e)))
        except CalledProcessError as e:
            self.__shell.writer.add("{0}\n".format(str(e)))


class History:

    def __init__(self):
        self.__commands = []
        self.__selectedIndex = 0

    def add(self, command):
        self.__commands.append(command)
        self.__selectedIndex = len(self.__commands)

    def previous(self):
        if self.__selectedIndex - 1 >= 0:
            self.__selectedIndex -= 1
            return self.__commands[self.__selectedIndex]
        return None

    def next(self):
        if self.__selectedIndex + 1 < len(self.__commands):
            self.__selectedIndex += 1
            return self.__commands[self.__selectedIndex]
        return None

    def last(self):
        if len(self.__commands) != 0:
            return self.__commands[-1]
        return None


class Shell:

    def __init__(self):
        self.__initEnvironment()
        self.__initConfig()
        self.__initHistory()
        self.__initLogging()
        self.__initWindow()

        self.__jobs = []

        logging.info("Starting writer...")
        self.writer = Shell.Writer(self.__window)
        self.writer.start()

    def __initConfig(self):
        self.__config = {}

        prompt = "{0} $".format(self.__environment["HOME"])
        self.__config["PROMPT"] = prompt.replace(
            self.__environment["HOME"], "~")

    def __initEnvironment(self):
        self.__environment = {}

        self.__environment["HOME"] = environ.get("HOME")
        self.__environment["PWD"] = environ.get("PWD")

    def __initHistory(self):
        self.history = History()

    def __initLogging(self):
        logging.basicConfig(filename="debug.log", level=logging.DEBUG)

    def __initWindow(self):
        self.__window = initscr()
        noecho()
        cbreak()
        self.__window.keypad(True)

    def __deinitWriter(self):
        logging.info("Stopping writer...")
        self.writer.stop()
        self.writer.join()

    def __deinitWindow(self):
        logging.info("Destructing window...")
        nocbreak()
        self.__window.keypad(False)
        echo()

    def run(self):
        try:
            while True:
                self.writer.add("\r{0}".format(self.__config["PROMPT"]))
                self.__fetch()
                self.__execute()
        except Exception as e:
            logging.info(e)
        finally:
            self.__deinitWriter()
            self.__deinitWindow()
            logging.info("Application closing.")

    def __fetch(self):
        command = ""

        while True:
            character = self.__window.getch()

            if character == curses.KEY_ENTER or character == 10:
                if len(command.strip()) != 0:
                    command += "\n"
                    break
            elif character == curses.KEY_BACKSPACE:
                command = command[0:-1]
            else:
                command += chr(character)
            self.writer.add("\r{0}{1}".format(
                self.__config["PROMPT"], command))

        self.writer.add("\n")
        self.history.add(command.strip())

    def __execute(self):
        # TODO: Check whether to execute in background.
        command = self.history.last()
        executeBackground = False
        if command.split()[-1] == "&":
            executeBackground = True

        self.__jobs.append(Job(self, command))
        self.__jobs[-1].start()

        if not executeBackground:
            self.__jobs[-1].join()
        else:
            logging.info(
                "Started job {0} in background...".format(self.jobs[-1].id))

    class Writer(Thread):

        class Cursor:

            def __init__(self, x=0, y=0):
                self.x = x
                self.y = y

            def move(self, x, y):
                self.x = x
                self.y = y

            def reset(self):
                self.x = 0

            def left(self):
                self.x -= 1

            def right(self):
                self.x += 1

            def up(self):
                self.y -= 1

            def down(self):
                self.y += 1

        def __init__(self, window):
            super(Shell.Writer, self).__init__()
            self.__cursor = Shell.Writer.Cursor(0, 0)
            self.__stopCalled = False

            self.__queue = Queue()
            self.__window = window

        def add(self, message):
            if message is not None:
                self.__queue.put(message)

        def run(self):
            while not self.__stopCalled:
                if not self.__queue.empty():
                    message = self.__queue.get()
                    self.__print(message)
                    self.__window.move(self.__cursor.y, self.__cursor.x)
                    self.__window.refresh()
            sleep(0.1)

        def stop(self):
            self.__stopCalled = True

        def __print(self, message):
            # TODO: Add scrolling.

            for character in message:
                if character == "\n":
                    self.__cursor.reset()
                    self.__cursor.down()
                elif character == "\r":
                    self.__cursor.reset()
                    self.__window.clrtoeol()
                else:
                    self.__window.addch(
                        self.__cursor.y, self.__cursor.x, character)
                    self.__cursor.right()

if __name__ == "__main__":
    sh = Shell()
    sh.run()