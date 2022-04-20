import locale
import os
import sys
import select
import termios
import tty
import pty
from subprocess import Popen
import concurrent.futures
from logger import Logger


if __name__ == '__main__':
    term = '/bin/bash'
    home_default = os.path.join(os.path.dirname(__file__), "sessions")
    # command = 'docker run -it --rm centos /bin/bash'.split()

    print(f"Welcome to logterm: using local {term}.\n")
    session_name = input("Choose a name for this session: ")
    session_home = input("Choose a folder to store logs: ")

    if not os.path.exists(session_home):
        try:
            os.makedirs(session_home)
        except:
            print(f"home could not be created, defaulting to: {home_default}")
            session_home = home_default

    session_home = os.path.abspath(session_home)
    log_class = Logger(session_home, session_name)

    prep_command = \
        f"export PROMPT_COMMAND='echo \"$(date \"+%Y-%m-%d.%H:%M:%S\") $(history 1)\" >> " \
        f"{log_class.cmd_file} && echo \"$PATH:$PWD:::$(history 1)\" >> {log_class.paths_file}'"

    print("\nSession started. Remember: if you change user, you must run the command below again!")
    print(f"RUN THIS: {prep_command}\n")

    # save original tty setting then set it to raw mode
    old_tty = termios.tcgetattr(sys.stdin)
    tty.setraw(sys.stdin.fileno())

    # open pseudo-terminal to interact with subprocess
    master_fd, slave_fd = pty.openpty()

    # use os.setsid() make it run in a new process group, or bash job control will not be enabled
    p = Popen(term,
              preexec_fn=os.setsid,
              stdin=slave_fd,
              stdout=slave_fd,
              stderr=slave_fd,
              universal_newlines=True)

    prep_command = bytes(prep_command, encoding=locale.getlocale()[1]) + b'\r'
    must_prep = True

    with concurrent.futures.ThreadPoolExecutor() as executor:
        video_future = executor.submit(log_class.record_video)
        hashes_future = executor.submit(log_class.start_hash_check, prep_command)

        while p.poll() is None:
            r, w, e = select.select([sys.stdin, master_fd], [], [])
            if must_prep:
                os.write(master_fd, prep_command)
                must_prep = False

            if sys.stdin in r:
                d = os.read(sys.stdin.fileno(), 10240)
                os.write(master_fd, d)

            elif master_fd in r:
                o = os.read(master_fd, 10240)
                if o:
                    os.write(sys.stdout.fileno(), o)

        log_class.stop_video()
        log_class.stop_hash_check()

        print("\rSaving video information, please wait...")
        while not video_future.done():
            pass
        exc = video_future.exception()
        if exc is None:
            print("\rVideo saved successfully")
        else:
            print(f"\rVideo could not be saved because of: {exc}")

        print("\rSaving hashes information, please wait...")
        while not hashes_future.done():
            pass
        exc = hashes_future.exception()
        if exc is None:
            print("\rHashes saved successfully")
        else:
            print(f"\rHashes could not be saved because of: {exc}")

        # restore tty settings back
    termios.tcsetattr(sys.stdin, termios.TCSADRAIN, old_tty)
