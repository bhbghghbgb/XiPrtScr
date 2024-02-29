import os
from collections import deque
from collections.abc import Iterable
from ctypes import Structure, byref, c_short, c_ubyte, c_ulong, c_ushort, windll
from dataclasses import dataclass
from datetime import datetime
from io import BytesIO
from queue import Empty, Queue
from time import time
from tkinter import filedialog, font, simpledialog
from tkinter.scrolledtext import ScrolledText
from typing import Any, Callable, Literal, TypeVar
from winsound import MessageBeep
import win32clipboard
from PIL import Image, ImageGrab, ImageTk, UnidentifiedImageError
from tkscrolledframe import ScrolledFrame

import ttkoverride as tkinter

_T = TypeVar("_T")


class Constants:
    WIDTH = 192
    HEIGHT = 108
    COLUMN = 6
    PADDING = 5
    MAGIC = 2
    LIMIT = 256
    SUPPORTED_FILETUPLES = tuple(
        (desc, ext)
        for ext, desc in Image.registered_extensions().items()
        if desc != "PDF"
    )
    SUPPORTED_FILETYPES = tuple(ext for _, ext in SUPPORTED_FILETUPLES)

    XINPUT_GAMEPAD_DPAD_UP = 0x0001
    XINPUT_GAMEPAD_DPAD_DOWN = 0x0002
    XINPUT_GAMEPAD_DPAD_LEFT = 0x0004
    XINPUT_GAMEPAD_DPAD_RIGHT = 0x0008
    XINPUT_GAMEPAD_START = 0x0010
    XINPUT_GAMEPAD_BACK = 0x0020
    XINPUT_GAMEPAD_LEFT_THUMB = 0x0040
    XINPUT_GAMEPAD_RIGHT_THUMB = 0x0080
    XINPUT_GAMEPAD_LEFT_SHOULDER = 0x0100
    XINPUT_GAMEPAD_RIGHT_SHOULDER = 0x0200
    XINPUT_GAMEPAD_A = 0x1000
    XINPUT_GAMEPAD_B = 0x2000
    XINPUT_GAMEPAD_X = 0x4000
    XINPUT_GAMEPAD_Y = 0x8000
    FPS = 10
    FRAMETIME = int(1 / FPS * 1000)
    DELAY = 0.15


class XInput:
    class XINPUT_STATE(Structure):
        class XINPUT_GAMEPAD(Structure):
            _fields_ = [
                ("wButtons", c_ushort),
                ("bLeftTrigger", c_ubyte),
                ("bRightTrigger", c_ubyte),
                ("sThumbLX", c_short),
                ("sThumbLY", c_short),
                ("sThumbRX", c_short),
                ("sThumbRY", c_short),
            ]

        _fields_ = [("dwPacketNumber", c_ulong), ("Gamepad", XINPUT_GAMEPAD)]

    @dataclass
    class MappedStates:
        PacketNumber: int = 0
        LeftTrigger: int = 0
        RightTrigger: int = 0
        ThumbLX: int = 0
        ThumbLY: int = 0
        ThumbRX: int = 0
        ThumbRY: int = 0
        DpadUp: bool = False
        DpadDown: bool = False
        DpadLeft: bool = False
        DpadRight: bool = False
        Start: bool = False
        Back: bool = False
        LeftThumb: bool = False
        RightThumb: bool = False
        LeftShoulder: bool = False
        RightShoulder: bool = False
        A: bool = False
        B: bool = False
        X: bool = False
        Y: bool = False

    @dataclass
    class Event:
        type: Literal["press", "release", "any"]
        key: Literal["LeftTrigger", "RightTrigger", "Any"]

        def __eq__(self, other):
            return (
                self.type == other.type or self.type == "any" or other.type == "any"
            ) and (self.key == other.key or self.key == "Any" or other.key == "Any")

    def __init__(
        self, *registering_callbacks: tuple[Event, Callable[[MappedStates], Any]]
    ):
        self.__dll = windll.xinput1_4
        self.__prev_states = self.MappedStates()
        self.__event_queue: Queue[XInput.Event] = Queue()
        self.__registered_callbacks: list[
            tuple[XInput.Event, Callable[[XInput.MappedStates], Any]]
        ] = []
        for callback in registering_callbacks:
            self.register_callback(callback)

    def poll(self):
        new_states = self.XINPUT_STATE()
        if not self.__dll.XInputGetState(0, byref(new_states)):
            return self.read_raw_states(new_states)

    def __update_states(self, new_states: MappedStates):
        if self.__prev_states.PacketNumber == new_states.PacketNumber:
            return
        # NOTE: only LT/RT max rn
        if self.__prev_states.LeftTrigger != new_states.LeftTrigger:
            if new_states.LeftTrigger == 255:
                self.__event_queue.put(XInput.Event("press", "LeftTrigger"))
            elif new_states.LeftTrigger == 0:
                self.__event_queue.put(XInput.Event("release", "LeftTrigger"))
        if self.__prev_states.RightTrigger != new_states.RightTrigger:
            if new_states.RightTrigger == 255:
                self.__event_queue.put(XInput.Event("press", "RightTrigger"))
            elif new_states.RightTrigger == 0:
                self.__event_queue.put(XInput.Event("release", "RightTrigger"))
        self.__prev_states = new_states

    def __handle_events(self):
        try:
            while event := self.__event_queue.get_nowait():
                for callback in self.__registered_callbacks:
                    if callback[0] == event:
                        callback[1](self.__prev_states)
        except Empty:
            pass

    def register_callback(self, callback: tuple[Event, Callable[[MappedStates], Any]]):
        self.__registered_callbacks.append(callback)

    def update(self):
        if new_states := self.poll():
            self.__update_states(new_states)
        self.__handle_events()

    @staticmethod
    def read_raw_states(raw_states: XINPUT_STATE):
        return XInput.MappedStates(
            PacketNumber=raw_states.dwPacketNumber,
            LeftTrigger=raw_states.Gamepad.bLeftTrigger,
            RightTrigger=raw_states.Gamepad.bRightTrigger,
            ThumbLX=raw_states.Gamepad.sThumbLX,
            ThumbLY=raw_states.Gamepad.sThumbLY,
            ThumbRX=raw_states.Gamepad.sThumbRX,
            ThumbRY=raw_states.Gamepad.sThumbRY,
            DpadUp=bool(raw_states.Gamepad.wButtons & Constants.XINPUT_GAMEPAD_DPAD_UP),
            DpadDown=bool(
                raw_states.Gamepad.wButtons & Constants.XINPUT_GAMEPAD_DPAD_DOWN
            ),
            DpadLeft=bool(
                raw_states.Gamepad.wButtons & Constants.XINPUT_GAMEPAD_DPAD_LEFT
            ),
            DpadRight=bool(
                raw_states.Gamepad.wButtons & Constants.XINPUT_GAMEPAD_DPAD_RIGHT
            ),
            Start=bool(raw_states.Gamepad.wButtons & Constants.XINPUT_GAMEPAD_START),
            Back=bool(raw_states.Gamepad.wButtons & Constants.XINPUT_GAMEPAD_BACK),
            LeftThumb=bool(
                raw_states.Gamepad.wButtons & Constants.XINPUT_GAMEPAD_LEFT_THUMB
            ),
            RightThumb=bool(
                raw_states.Gamepad.wButtons & Constants.XINPUT_GAMEPAD_RIGHT_THUMB
            ),
            LeftShoulder=bool(
                raw_states.Gamepad.wButtons & Constants.XINPUT_GAMEPAD_LEFT_SHOULDER
            ),
            RightShoulder=bool(
                raw_states.Gamepad.wButtons & Constants.XINPUT_GAMEPAD_RIGHT_SHOULDER
            ),
            A=bool(raw_states.Gamepad.wButtons & Constants.XINPUT_GAMEPAD_A),
            B=bool(raw_states.Gamepad.wButtons & Constants.XINPUT_GAMEPAD_B),
            X=bool(raw_states.Gamepad.wButtons & Constants.XINPUT_GAMEPAD_X),
            Y=bool(raw_states.Gamepad.wButtons & Constants.XINPUT_GAMEPAD_Y),
        )


class ImageComposite:
    def __init__(self, image: Image.Image, filename: str):
        self.filename = os.path.splitext(os.path.basename(filename))[0]
        self.truemage = image
        self.viewmage = ImageTk.PhotoImage(
            image.resize((Constants.WIDTH, Constants.HEIGHT), Image.Resampling.LANCZOS)
        )
        self.pinnation = tkinter.BooleanVar()

    def __str__(self):
        return f'{"Pinned" if self.pinnation.get() else "Unpinned"} N:<{self.filename}> T:{self.truemage} V:{repr(self.viewmage)} S:{repr(self)}'


class App:
    def __init__(self):
        self._root = tkinter.Tk()
        self._root.title("Screenshot Catcher")
        self._style = tkinter.Style(self._root)
        self._themes = self._style.theme_names()
        self._menu = tkinter.Menu(self._root)
        self._root.configure(menu=self._menu)
        self._view_menu = tkinter.Menu(self._menu, tearoff=False)
        self._action_menu = tkinter.Menu(self._menu, tearoff=False)
        self._option_menu = tkinter.Menu(self._menu, tearoff=False)
        self._view_menu.add_command(
            label="Rotate", underline=1, command=self._command_view_rotate
        )
        self._view_menu.add_command(
            label="Rrotate", underline=3, command=self._command_view_rrotate
        )
        self._view_menu.add_command(
            label="Rotate by...", underline=7, command=self._command_view_nrotate
        )
        self._view_menu.add_separator()
        self._view_menu.add_command(
            label="Remove all", underline=0, command=self._command_view_remove_all
        )
        self._view_menu.add_separator()
        self._view_themes_menu = tkinter.Menu(self._menu, tearoff=False)
        self._current_theme = tkinter.StringVar(self._root)
        for theme in self._themes:
            self._view_themes_menu.add_radiobutton(
                label=theme,
                variable=self._current_theme,
                value=theme,
                command=self._command_view_change_theme,
            )
        self._view_menu.add_cascade(
            label="Themes", underline=0, menu=self._view_themes_menu
        )
        self._current_theme.set("xpnative")
        self._command_view_change_theme()
        self._view_menu.add_separator()
        self._view_menu.add_command(label="0/0", state=tkinter.DISABLED)
        self._action_menu.add_command(
            label="Take", underline=0, command=self._command_action_take
        )
        self._action_menu.add_command(
            label="Grab", underline=0, command=self._command_action_grab
        )
        self._action_menu.add_command(
            label="Load files...", underline=0, command=self._command_action_load_files
        )
        self._action_menu.add_command(
            label="Load dir...", underline=5, command=self._command_action_load_dir
        )
        self._action_menu.add_separator()
        self._action_menu.add_command(
            label="Save all", underline=0, command=self._command_action_save_all
        )
        self._overwrite_save = tkinter.BooleanVar(self._root, False)
        self._option_menu.add_checkbutton(
            label="Save overwrite?", underline=5, variable=self._overwrite_save
        )
        self._xinput_poll = tkinter.BooleanVar(self._root, False)
        self._option_menu.add_checkbutton(
            label="LT/RT take?",
            underline=0,
            variable=self._xinput_poll,
            command=self.__poll_for_xinput,
        )
        self._copy_upon_take = tkinter.BooleanVar(self._root, True)
        self._option_menu.add_checkbutton(
            label="Copy upon Take?", underline=5, variable=self._copy_upon_take
        )
        self._option_menu.add_separator()
        self._option_menu.add_command(
            label="Collect limit...",
            underline=0,
            command=self._command_option_set_deque_limit,
        )
        self._option_menu.add_command(
            label="Magic number...",
            underline=0,
            command=self._command_option_set_magic_number,
        )
        self._option_menu.add_command(
            label="XInput cooldown...",
            underline=0,
            command=self._command_option_set_xinput_take_cooldown,
        )
        self._option_menu.add_command(
            label="Save directory...",
            underline=5,
            command=self._command_option_set_save_path,
        )
        self._menu.add_cascade(label="View", underline=0, menu=self._view_menu)
        self._menu.add_cascade(label="Action", underline=0, menu=self._action_menu)
        self._menu.add_cascade(label="Option", underline=0, menu=self._option_menu)
        self._frame = ScrolledFrame(self._root, scrollbars="both", use_ttk=True)
        self._frame.pack(side="top", expand=True, fill="both")
        self._frame.bind_scroll_wheel(self._root)
        self._labels_frame = self._frame.display_widget(tkinter.Frame)
        self._images: deque[ImageComposite] = deque(maxlen=Constants.LIMIT)
        self._deque_collect_limit = Constants.LIMIT
        self._magic_number = Constants.COLUMN
        self._xinput_take_cooldown = Constants.DELAY
        self._save_path = "."
        self.__xinput = XInput(
            (
                XInput.Event("press", "LeftTrigger"),
                self._xinput_ltrt_command_action_take,
            ),
            (
                XInput.Event("press", "RightTrigger"),
                self._xinput_ltrt_command_action_take,
            ),
        )
        self._xinput_last_time = time()
        self.__font_pinned = font.nametofont("TkDefaultFont").copy()
        self.__font_pinned.configure(slant=font.ITALIC, underline=True)

        self._refresh_gui()

    def _reset_images(self, images: Iterable[ImageComposite]):
        self._images = deque(images, maxlen=self._deque_collect_limit)
        self._refresh_gui()

    def _refresh_gui(self):
        self._clear_gui()
        for index, image in enumerate(self._images):
            label = tkinter.Label(
                self._labels_frame,
                text=image.filename,
                image=image.viewmage,
                compound=tkinter.TOP,
                #   width=Constants.WIDTH+2*Constants.MAGIC,
                takefocus=True,
                borderwidth=Constants.MAGIC,
                relief="raised",
                font=self.__font_pinned if image.pinnation.get() else None,
            )  # type: ignore
            self._bind_context_menu(image, label)
            label.grid(
                column=index % self._magic_number,
                row=index // self._magic_number,
                padx=Constants.PADDING,
                pady=Constants.PADDING,
                ipadx=Constants.MAGIC,
                ipady=Constants.MAGIC,
            )
        self._view_menu.entryconfigure(
            8, label=f"{len(self._images)}/{self._deque_collect_limit}"
        )

    def _bind_context_menu(self, image: ImageComposite, label: tkinter.Label):
        context_menu = tkinter.Menu(label, tearoff=False)
        context_menu.add_command(
            label="Copy",
            underline=0,
            command=lambda img=image: self.copy_image(img.truemage),
        )
        context_menu.add_command(
            label="Save",
            underline=0,
            command=lambda img=image: self.save_image(img.truemage, img.filename),
        )
        context_menu.add_command(
            label="Save as...",
            underline=1,
            command=lambda img=image: self.saveas_image(img.truemage, img.filename),
        )
        context_menu.add_separator()
        context_menu.add_command(
            label="Remove",
            underline=0,
            command=lambda img=image: self._remove_collected_image(img),
        )
        context_menu.add_separator()
        context_menu.add_checkbutton(
            label="Pin?",
            underline=0,
            variable=image.pinnation,
            command=self._refresh_gui,
        )
        label.bind(
            "<Button-3>",
            lambda event, ctx=context_menu: ctx.post(event.x_root, event.y_root),
        )

    def _clear_gui(self):
        for label in self._labels_frame.winfo_children():
            label.destroy()
        # https://stackoverflow.com/questions/59584847/how-to-shrink-a-frame-in-tkinter-after-removing-contents
        self._labels_frame.configure(height=1)

    def _remove_collected_image(self, image: ImageComposite):
        self._images.remove(image)
        self._refresh_gui()

    def _command_view_rotate(self):
        self._images.rotate()
        self._refresh_gui()

    def _command_view_rrotate(self):
        self._images.rotate(-1)
        self._refresh_gui()

    def _command_view_nrotate(self):
        self._images.rotate(
            simpledialog.askinteger(
                "Rotate view",
                "Rotate view (enter negative to rrotate) by:",
                initialvalue=0,
                parent=self._root,
            )
            or 0
        )
        self._refresh_gui()

    def _command_view_remove_all(self):
        self._reset_images(image for image in self._images if image.pinnation.get())

    def _command_view_change_theme(self):
        self._change_theme(self._current_theme.get())

    def _command_action_take(self):
        image = ImageGrab.grab()
        if self._copy_upon_take.get():
            self.copy_image(image)
        self.add_image(image, f"PrtSc {self.datetimenow()}")

    def _command_action_grab(self):
        image = ImageGrab.grabclipboard()
        if isinstance(image, list):
            self.add_images(self.open_images(image))
        elif isinstance(image, Image.Image):
            self.add_image(image, f"ClpBd {self.datetimenow()}")

    def _command_action_save_all(self):
        progress_window = tkinter.Toplevel(self._root)
        progress_window.grab_set()
        progress_window.wm_title(f"Saving {len(self._images)} images")
        progress_label = tkinter.Label(progress_window, text="Start save command")
        progress_label.grid(
            row=0,
            column=0,
            columnspan=2,
            padx=Constants.PADDING,
            pady=Constants.PADDING,
        )
        progress_bar = tkinter.Progressbar(
            progress_window, length=500, mode="indeterminate", maximum=50
        )
        progress_bar.grid(
            row=1, column=0, padx=Constants.PADDING, pady=Constants.PADDING
        )
        progress_bar.start()
        progress_bar_percentage = tkinter.Label(progress_window, text="00.00%")
        progress_bar_percentage.grid(
            row=1, column=1, padx=Constants.PADDING, pady=Constants.PADDING
        )
        progress_log = ScrolledText(
            progress_window, wrap=tkinter.WORD, width=60, height=10, font="Consolas"
        )
        progress_log.grid(
            row=2,
            column=0,
            columnspan=2,
            padx=Constants.PADDING,
            pady=Constants.PADDING,
        )
        progress_log.insert(tkinter.END, "Start save command")
        if not len(self._images):
            progress_log.insert(tkinter.END, "\nNothing to save")
            return
        progress_bar.stop()
        progress_bar["mode"] = "determinate"
        progress_bar["value"] = 0
        progress_bar["maximum"] = len(self._images)
        error_count = 0
        for index, image in enumerate(self._images):
            progress_label["text"] = (
                f"Saving image {index+1} of {len(self._images)}. Errored {error_count}"
            )
            progress_log.insert(
                tkinter.END, f"\nSaving image {index+1}/{len(self._images)} {image}"
            )
            self._root.update()
            path, e = self.save_image(image.truemage, image.filename)
            # sleep(1)
            if e:
                error_count += 1
                progress_log.insert(tkinter.END, f"\nError saving {path}: {e}")
            else:
                progress_log.insert(tkinter.END, f"\nOk saving {path}")
            progress_label["text"] = (
                f"Saved image {index+1} of {len(self._images)}. Errored {error_count}"
            )
            progress_bar["value"] = index + 1
            progress_bar_percentage["text"] = "{:05.2f}%".format(
                (index + 1) / len(self._images) * 100
            )

        progress_log.insert(
            tkinter.END,
            f"\nSaved {len(self._images)-error_count}/{len(self._images)} images. Errored {error_count}",
        )
        progress_log.insert(tkinter.END, "\nThe operation completed successfully.")
        progress_bar["maximum"] = 50
        progress_bar["mode"] = "indeterminate"
        progress_bar.start()

    def _command_action_load_files(self):
        files = filedialog.askopenfilenames(
            initialdir=".",
            parent=self._root,
            title="Select files to load",
            filetypes=Constants.SUPPORTED_FILETUPLES,
        )
        if files:
            self.add_images(self.open_images(files))

    def _command_action_load_dir(self):
        path = filedialog.askdirectory(
            initialdir=".",
            mustexist=True,
            parent=self._root,
            title="Select directory to load from",
        )
        if path:
            self.add_images(
                self.open_images(os.path.join(path, file) for file in os.listdir(path))
            )

    def _command_option_set_deque_limit(self):
        self._deque_collect_limit = (
            simpledialog.askinteger(
                "Enter the new deque limit",
                "Enter the new deque limit (max images to collect):",
                initialvalue=self._deque_collect_limit,
                minvalue=1,
                maxvalue=256,
                parent=self._root,
            )
            or self._deque_collect_limit
        )
        self._reset_images(self._images)
        self._refresh_gui()

    def _command_option_set_magic_number(self):
        self._magic_number = (
            simpledialog.askinteger(
                "Enter the new magic number",
                "Enter the new column count:",
                initialvalue=self._magic_number,
                minvalue=1,
                maxvalue=9,
                parent=self._root,
            )
            or self._magic_number
        )
        self._refresh_gui()

    def _command_option_set_xinput_take_cooldown(self):
        self._xinput_take_cooldown = (
            simpledialog.askfloat(
                "Enter the new XInput cooldown",
                "Enter the new cooldown time between Take with XInput LT/RT:",
                initialvalue=self._xinput_take_cooldown,
                minvalue=0.1,
                maxvalue=1,
                parent=self._root,
            )
            or self._xinput_take_cooldown
        )

    def _command_option_set_save_path(self):
        self._save_path = (
            filedialog.askdirectory(initialdir=self._save_path, parent=self._root)
            or self._save_path
        )

    def _xinput_ltrt_command_action_take(self, states: XInput.MappedStates):
        if time() - self._xinput_last_time < self._xinput_take_cooldown:
            return
        if states.LeftTrigger != 255 or states.RightTrigger != 255:
            return
        MessageBeep()
        self._command_action_take()
        self._xinput_last_time = time()

    def _change_theme(self, theme_name: str):
        self._style.theme_use(theme_name)

    def add_image(self, image: Image.Image, filename: str):
        # self._images.append(ImageComposite(image, filename))
        self.deque_append_with_predicate(
            self._images,
            ImageComposite(image, filename),
            lambda image: image.pinnation.get(),
        )
        self._refresh_gui()

    def add_images(self, images: Iterable[tuple[Image.Image, str]]):
        # self._images.extend(ImageComposite(image, filename) for image, filename in images)
        self.deque_extend_with_predicate(
            self._images,
            (ImageComposite(image, filename) for image, filename in images),
            lambda image: image.pinnation.get(),
        )
        self._refresh_gui()

    @staticmethod
    def copy_image(image: Image.Image):
        with BytesIO() as output:
            image.convert("RGB").save(output, "BMP")
            data = output.getvalue()[14:]
        win32clipboard.OpenClipboard()
        win32clipboard.EmptyClipboard()
        win32clipboard.SetClipboardData(win32clipboard.CF_DIB, data)
        win32clipboard.CloseClipboard()

    def save_image(self, image: Image.Image, path: str, ext="PNG"):
        path = os.path.join(self._save_path, path)
        pathext = os.path.splitext(path)[1]
        if not pathext or pathext == ".":
            path = f"{path}.{ext.lower()}"
        if not os.path.isfile(path) or self._overwrite_save.get():
            try:
                image.save(path)
            except OSError as e:
                return path, e
            return path, None
        return path, "Existed"

    def saveas_image(self, image: Image.Image, name: str):
        path = filedialog.asksaveasfilename(
            defaultextension=os.path.splitext(name)[1] or ".png",
            initialfile=name,
            filetypes=Constants.SUPPORTED_FILETUPLES,
            parent=self._root,
        )
        if path:
            self.save_image(image, path)

    @staticmethod
    def datetimenow():
        return datetime.now().strftime("%Y_%m_%d %H_%M_%S_%f")

    @staticmethod
    def open_images(files: Iterable[str]):
        for file in files:
            if not file.endswith(Constants.SUPPORTED_FILETYPES):
                continue
            try:
                image = Image.open(file)
            except UnidentifiedImageError as e:
                print(e)
                continue
            yield image, file

    def __poll_for_xinput(self):
        if not self._xinput_poll.get():
            self._root.after_cancel(self.__xinput_polling_id)
            return
        self.__xinput.update()
        self.__xinput_polling_id = self._root.after(
            Constants.FRAMETIME, self.__poll_for_xinput
        )

    @staticmethod
    def deque_append_with_predicate(
        dq: deque[_T], __object: _T, predicate: Callable[[_T], bool]
    ):
        if len(dq) == dq.maxlen:
            for object in dq:
                if not predicate(object):
                    dq.remove(object)
                    break
            else:
                return
        dq.append(__object)

    @staticmethod
    def deque_extend_with_predicate(
        dq: deque[_T], __iter: Iterable[_T], predicate: Callable[[_T], bool]
    ):
        for __object in __iter:
            App.deque_append_with_predicate(dq, __object, predicate)


if __name__ == "__main__":
    app = App()
    tkinter.Style(app._root).theme_use("xpnative")
    tkinter.mainloop()
