import os
import hashlib
import cv2 as cv
import pyautogui
import numpy as np


class Logger:
    def __init__(self, session_home, session_name):
        self.hash_file = os.path.join(session_home, f"{session_name}_hashes.txt")
        self.paths_file = os.path.join(session_home, f"{session_name}_paths.txt")
        self.cmd_file = os.path.join(session_home, f"{session_name}_commands.txt")
        self.record_file = os.path.join(session_home, f"{session_name}_recording.avi")
        self.hc_break = False
        self.rv_break = False

    def start_hash_check(self, prep_command):
        last_mod = -1
        with open(self.hash_file, "a") as f:
            while not self.hc_break:
                try:
                    mod_at = os.path.getsize(self.paths_file)
                except FileNotFoundError:
                    continue
                except OSError:
                    continue

                if mod_at != last_mod:
                    last_mod = mod_at
                    with open(self.paths_file, "rb") as file:
                        last_line = file.readlines()[-1]
                        if prep_command in last_line or not last_line:
                            continue
                        else:
                            last_line = last_line.decode()
                    try:
                        upd = self.process_line(last_line)
                        f.write(upd)
                    except Exception:
                        pass

    def stop_hash_check(self):
        self.hc_break = True

    def record_video(self):
        screen_size = pyautogui.size()
        # initialize the object
        video = cv.VideoWriter(self.record_file,
                               cv.VideoWriter_fourcc(*'MJPG'),
                               60, screen_size)

        while not self.rv_break:
            screen_shot_img = pyautogui.screenshot()
            # convert into array
            frame = np.array(screen_shot_img)
            # change from BGR to RGB
            frame = cv.cvtColor(frame, cv.COLOR_BGR2RGB)
            # write frame
            video.write(frame)

        cv.destroyAllWindows()
        video.release()

    def stop_video(self):
        self.rv_break = True

    @staticmethod
    def process_line(line):
        path_list, command = line.split(':::')
        paths = path_list.split(':')
        command_els = command.split()[1:]
        to_ret = "\n" + command
        for el in command_els:
            if os.path.exists(el):
                to_hash = el
            elif not el.startswith('-'):
                to_hash = None
                for path in paths:
                    cand = os.path.join(path, el)
                    if os.path.exists(cand):
                        to_hash = cand
                        break
                if to_hash is None:
                    continue
            else:
                continue
            with open(to_hash, "rb") as f:
                b_data = f.read()
                c_hash = hashlib.sha1(b_data).hexdigest()
                to_ret += f"\n{to_hash}: {c_hash}"
        return to_ret
