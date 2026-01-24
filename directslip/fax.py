import dataclasses
import datetime
import pathlib

import time
import rich
import numpy as np
import PIL


import escpos
import escpos.printer

import usb

PAPER_STATUS_EMOJI = {
    0: "❌",
    1: "⚠️",
    2: "✅",
}

CP437_CHARS = ''.join(x.to_bytes(1, byteorder="big").decode("cp437") for x in range(0xff))

def to_cp437(x: str):
    return ''.join(
        y if y in CP437_CHARS else '?'
        for y in x
    )

def usb_get_backend():
    """Proper Windows USB backend"""
    try:
        import usb
        import usb.backend.libusb1           
    except ImportError:
        raise

    try:
        import libusb_package           
    except ImportError:
        raise

    return usb.backend.libusb1.get_backend(find_library=libusb_package.find_library)

def resize_img(img, max_width=512, force_portrait=False):
    if not force_portrait and img.size[0] > img.size[1]:
        img = img.rotate(90, expand=True)
    if img.size[0] > max_width:
            new_height = int(img.size[1] * max_width / img.size[0])
            if new_height <= 0:
                raise RuntimeError(f"Cannot reduce height to 0")
            new_size = (max_width, new_height)
            img = img.resize(new_size, PIL.Image.Resampling.LANCZOS)
    return img

# TODO PYDANTIC
@dataclasses.dataclass
class Fax:
    sender: str | None = None
    msg: str = ""
    image: PIL.Image.Image | None = None
    timestamp: datetime.datetime = dataclasses.field(default_factory=lambda *args, **kwargs: datetime.datetime.now())
    force_portrait: bool = False
    is_scan: bool = False

    def __post_init__(self):
        if self.msg is not None:
            self.msg = to_cp437(self.msg)

        if self.image is not None:
            if not isinstance(self.image, PIL.Image.Image):
                raise RuntimeError(f"Unsupported image type `{type(self.image)}`")
            
            self.image = resize_img(self.image, force_portrait=self.force_portrait)

            # Scan
            if self.is_scan:
                pass # TODO Cant opencv on pi zero
                #import cv as cv
                #self.image = cv.adaptiveThreshold(
                #    np.array(self.image),  # No need RGB / BGR Madness
                #    255,
                #    cv.ADAPTIVE_THRESH_GAUSSIAN_C,
                #    cv.THRESH_BINARY,
                #    63, # Block size 7
                #    8   # Float 2
                #)
                #self.image = PIL.Image.fromarray(self.image)


    def get_str_content(self):
        res = [
            f"FROM       : {self.sender if self.sender else '<UNKNOWN>'}",
            f"RECEIVED AT: {self.timestamp.isoformat(timespec='seconds')}",
        ]
        if self.msg:
            res.append("\n\n")  # TODO More ?
            res.append(self.msg)

        return res

    def print(self, p):
        p.line_spacing(0)
        p.set_with_default(font="b")
        for x in self.get_str_content():
            p.textln(x)  # UNSURE MULTILINE
        p.line_spacing()
        p.set_with_default()

        if self.image is not None:
            p.ln()
            p.image(self.image)

        p.cut()  # TODO feed=False

    def print_dummy(self, p=None):
        for x in self.get_str_content():
           rich.print(x)

        if self.image is not None:
            rich.print(type(self.image), self.image)


def get_test_fax():
    """Test Fax"""
    test_image_path = pathlib.Path(__file__).parent / "assets" / "1F9FE_color_cropped.png"  # TODO RESIZE full size ? use a square ?
    return Fax("TEST_USER", "THIS IS A TEST MESSAGE", PIL.Image.open(test_image_path))  # Force protrait


class Printer:
    def __init__(
        self,
        config
    ):
        usb_args = {}
        if config.get("use_libusb1", False):
            usb_args["backend"] = usb_get_backend()
        self.p = escpos.printer.Usb(**config, usb_args=usb_args)
        # idVendor, idProduct, timeout=0, timeout=0, in_ep, out_ep => , 0x81, 0x02

    def is_printer_ok(self):
        try:
            if not self.p.is_usable():
                print(f"Printer KO: Missing driver")
                return False
            if not self.p.is_online():
                # TRY BOOT
                print("Printer not online, waiting...")
                self.p.hw("INIT")
                time.sleep(0.75)  # TODO LESS ?
                if not self.p.is_online():
                    print(f"Printer did not boot in time")
                    return False  # TODO Return ORANGE status ?


        except escpos.exceptions.DeviceNotFoundError as exc:
            print(f"Printer KO: Unable to open printer device, it is surely offline")
            self.p._device = False
            return False
        except usb.core.USBError as exc:
            print(f"Printer KO: Printer device unreachable, likely lost connection")
            self.p._device.reset()  # TODO TRY
            self.p.close() # This is cleaner and possible here since we have a device
            return False
            # self.p.open()
        # except Exception as exc:
        #     print(f"OTHER EXC: {type(exc)} {exc}")
        #     self.p.device = None


        return True

    def status(self):
        is_ok = self.is_printer_ok()
        if not is_ok:
            return False, False, False
        return True, self.p.is_online(), self.p.paper_status()

    def status_str(self):
        ok, online, paper = self.status()
        if not ok:
            return "OFFLINE ❌"

        return f"ONLINE ✅:\n  PAPER: {PAPER_STATUS_EMOJI[paper]}"
