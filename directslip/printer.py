import rich

import dataclasses
import datetime
import pathlib

import time
import rich
#import numpy as np # TODO
import PIL # already within python-escpos


import escpos
import escpos.printer

import usb


PAPER_STATUS_EMOJI = {
    0: "❌",
    1: "⚠️",
    2: "✅",
}

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


    def print_test(self):
        #self.print_text("Test Print")

        for line_spacing in [0,96,128,192,255]:
            self.p.line_spacing(line_spacing)
            self.p.textln("Test Print")
        self.p.line_spacing()
        self.p.cut()

        #if self.image is not None:
        #    p.ln()
        #    p.image(self.image)

        #self.p.cut()  # TODO feed=False

    def print_text(self, text, line_spacing: int = 0, font_alt=False):
        """Print Text: 0<=line_spacing<=255"""
        self.p.line_spacing(line_spacing)
        if font_alt:
          self.p.set_with_default(font="b")
        self.p.textln(text)
        self.p.line_spacing()
        self.p.set_with_default()

        self.p.cut() # todo feed=False
