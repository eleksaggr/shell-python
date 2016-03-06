import curses
from curses import cbreak, echo, endwin, initscr, nocbreak, noecho
import logging
from os import environ
from time import sleep
from threading import Thread
from queue import Queue


class Shell:

    def __init__(self):
        self.__initEnvironment()
        self.__initConfig()
        self.__initLogging()
        self.__initWindow()

        logging.info("Starting writer...")
        self.writer = Shell.Writer(self.window)
        self.writer.start()

    def __initConfig(self):
        self.config = {}

        prompt = "{0} $".format(self.environment["HOME"])
        self.config["PROMPT"] = prompt.replace(
            self.environment["HOME"], "~")

    def __initEnvironment(self):
        self.environment = {}

        self.environment["HOME"] = environ.get("HOME")
        self.environment["PWD"] = environ.get("PWD")

    def __initLogging(self):
        logging.basicConfig(filename="debug.log", level=logging.DEBUG)

    def __initWindow(self):
        self.window = initscr()
        noecho()
        cbreak()
        self.window.keypad(True)

    def __deinitWriter(self):
        logging.info("Stopping writer...")
        self.writer.stop()
        self.writer.join()

    def __deinitWindow(self):
        logging.info("Destructing window...")
        nocbreak()
        self.window.keypad(False)
        echo()

    def run(self):
        try:
            while True:
                self.writer.add(self.config["PROMPT"])
                self.fetch()
        except Exception as e:
            logging.info(e)
        finally:
            self.__deinitWriter()
            self.__deinitWindow()
            logging.info("Application closing.")

    def fetch(self):
        command = ""

        while True:
            character = self.window.getch()

            if character == curses.KEY_ENTER or character == 10:
                command += "\n"
                break
            elif character == curses.KEY_BACKSPACE:
                command = command[0:-1]
            else:
                command += chr(character)
            self.writer.add("\r{0}{1}".format(self.config["PROMPT"], command))
        self.writer.add("\n")

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
            self.cursor = Shell.Writer.Cursor(0, 0)
            self.stopCalled = False

            self.queue = Queue()
            self.window = window

        def add(self, message):
            if message is not None:
                logging.info("Added the message: {0}".format(message))
                self.queue.put(message)

        def run(self):
            while not self.stopCalled:
                logging.info("Queue empty")
                if not self.queue.empty():
                    message = self.queue.get()
                    logging.info("Print: {0}".format(message))
                    self.__print(message)
                    self.window.move(self.cursor.y, self.cursor.x)
                    self.window.refresh()
            sleep(0.1)

        def stop(self):
            self.stopCalled = True

        def __print(self, message):
            for character in message:
                if character == "\n":
                    self.cursor.reset()
                    self.cursor.down()
                elif character == "\r":
                    self.cursor.reset()
                else:
                    self.window.addch(self.cursor.y, self.cursor.x, character)
                    self.cursor.right()

if __name__ == "__main__":
    sh = Shell()
    sh.run()
