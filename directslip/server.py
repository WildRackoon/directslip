import argparse
import dataclasses
import datetime
import tomllib
import logging
import pathlib

import gradio as gr
import rich
import rich.logging

import directslip.fax


# Logging
logger = logging.getLogger("directslip")

# CONFIG
MAX_MSG_LEN = 56*200 # 44chars * N Lines  # Font b its 56
MAX_IMAGE_SIZE = (512, 512*10)
MIN_IMAGE_SIZE = (8, 8)

# GLOBAL STATE
PRINTER = None
CONFIG = None
USER_DB = None

# TODO BETTER CONFIG
# TODO https://github.com/gradio-app/gradio/blob/main/demo/rate_limit/run.py
def check_user_rate(user_name: str) -> bool:
    """Basic rate limiting"""
    if CONFIG["USER_RATE_LIMIT_PER_MINUTES"] == 0:
        return True

    if user_name not in USER_DB:
        logger.error(f"Check user rate for unknown user `{user_name}`")
        return False

    now = datetime.now()

    USER_DB[user_name]["use_history"] = [
        x for x in USER_DB[user_name]["use_history"] if x < now - datetime.timedelta(minutes=1)
    ]
    uses = len(USER_DB[user_name]["use_history"])
    if uses > CONFIG["USER_RATE_LIMIT_PER_MINUTES"]:
        logger.debug(f"User `{user_name}` is spamming at {uses}/min")
        return False
    
    USER_DB[user_name]["use_history"].append(now)

    return True


# TODO USE / PUT IN FAX MOD
# def is_valid_size(size):
#     # Check Max
#     if size[0] > MAX_IMAGE_SIZE[0] or size[1] > MAX_IMAGE_SIZE[1]:
#         return False
#     # Check resize
#     new_height = int(img.size[1] * max_width / img.size[0])
#     if new_height < MIN_IMAGE_SIZE[1]:
#             return False
#     return True


def send_msg(msg, image, input_params, request: gr.Request):  # name, image
    # Preprocessing
    msg = msg.strip()

    if not msg and image is None:
        gr.Warning(f"Please add a text and/or image to the message")
        raise gr.Error("No msg / image", visible=False, print_exception=False)

    if msg and len(msg) > MAX_MSG_LEN:
        gr.Warning(f"Text Message to long, should not exceed `{MAX_MSG_LEN}` characters")
        raise gr.Error("Msg too long", visible=False, print_exception=False)

    # Rate Limiting

    # TODO FACTORIZE
    # Check Printer
    if not PRINTER.is_printer_ok():
        raise gr.Error("FAX OFFLINE ❌: Retry later", print_exception=False)

    # Format Fax
    try:
        user_name = request.username if len(request.username) != 1 else "<ADMIN>"
        fax = directslip.fax.Fax(user_name, msg, image, force_portrait=False, is_scan=bool("scan" in input_params))  # Force protrait
    except Exception as exc:
        raise gr.Error("Error while creating message") from exc

    # Print
    try:
        fax.print(PRINTER.p)
        # fax.print_dummy(PRINTER.p)
    except Exception as exc:
        raise gr.Error("Error while sending message") from exc

    gr.Success("Fax Sent With success")


def clear_inputs(evt_data: gr.EventData):
    # rich.print(gr.EventData)  # CAN get evt_data.target and maybe gest its inputs 
    return None, None, None

def get_status():
    # TODO FACTORIZE
    if not PRINTER.is_printer_ok():
        raise gr.Error("FAX OFFLINE ❌: Retry later", print_exception=False)
    return PRINTER.status_str()

def create_ui(config):
    # image_box = gr.Image()

    with gr.Blocks(fill_height=True, title=config["SERVER_TITLE"],) as demo:

        title = gr.HTML(f"<h1>{config["SERVER_TITLE"]}</h1>")

        # STATUS
        with gr.Row():
            status_button = gr.Button("Get Status")
            status_box = gr.Textbox(label="Status", interactive=False, lines=3)
            status_button.click(fn=get_status, outputs=[status_box])
            demo.load(get_status, outputs=[status_box], api_visibility="private")

        # FORM
        with gr.Row():
            with gr.Column():
                notice = gr.HTML(
                    """
                    <p>Be mindful of the following limitations:</p>
                    <ul>
                        <li>Only a very limited set of characters is supported for now</li>
                        <li>Paper width is 42 characters wide, if you want to avoid text wrapping</li>
                        <li>Landscape images will be rotated for best resolution</li>
                    </ul>
                    """
                )
            with gr.Column():
                input_params = gr.CheckboxGroup(
                    [
                        ("Image is a scan (Paper document, receipt etc)", "scan"),
                    ],
                    label="Settings"
                )

        # with gr.Blocks(fill_height=True):
        input_msg = gr.Textbox(label="Message", placeholder="Fax Message", lines=5)
        input_img = gr.Image(label="Image Document", height=200, sources=['upload', 'clipboard'], type="pil", image_mode="L")  # pil is gr default mode

        # output_box = gr.Text(visible=False)

        btn_send = gr.Button("Send")
        btn_send.click(
            fn=send_msg,
            inputs=[
                input_msg,
                input_img,
                input_params
            ],
            # outputs=[output_box],
            api_name="send",
        ).success(
            clear_inputs, outputs=[input_msg, input_img, input_params], api_visibility="private"
        )

    return demo


def read_config(config_path: pathlib.Path, allow_missing=False) -> dict:
    try:
        if not config_path.is_file():
            if allow_missing:
                logger.warning("Configuration file missing: `{config_path}`")
                return {}
            raise RuntimeError(f"Config file {config_path} does not exists")
        with config_path.open("rb") as fh:
            return tomllib.load(fh)
    except tomllib.TOMLDecodeError as exc:
        logger.critical("Configuration file is invalid: `{config_path}`")
        logger.error(exc, exc_info=True)
        raise


def test_print():
    if not PRINTER.is_printer_ok():
        raise RuntimeError("Cannot connect to printer")
    fax = directslip.fax.get_test_fax()
    fax.print(PRINTER.p)


def _main():
    # Root Logger Preference
    glogger = logging.getLogger()
    glogger.handlers.clear()
    glogger.addHandler(rich.logging.RichHandler())

    # Logger Safety
    logger.setLevel(logging.DEBUG)

    # Args
    parser = argparse.ArgumentParser()
    parser.add_argument('-c', '--config')
    parser.add_argument('-u', '--user')
    parser.add_argument('-t', '--test', action="store_true")
    args = parser.parse_args()

    # Check Arguments
    config_path = pathlib.Path(args.config or "config.toml")
    if not config_path.is_file():
        logger.error(f"Config file does not exists: `{config_path}`")
        return
    user_path = pathlib.Path(args.user or "userdb.toml")
    if not user_path.is_file():
        logger.error(f"Config file does not exists: `{user_path}`")
        return

    # Read config
    global CONFIG
    CONFIG = read_config(config_path)
    if CONFIG is None:
        return
    CONFIG = read_config(pathlib.Path("defaults.toml")) | CONFIG

    # Set Log Level
    logger.setLevel(getattr(logging, CONFIG["LOG_LEVEL"]))

    # Dump Config
    logger.debug("Config:")
    for k,v in CONFIG.items():
        logger.debug(f"  {k:32} {v}")

    # Dump Users
    userdb = read_config(user_path, allow_missing=True)
    if not userdb:
        userdb={"admin": "admin"}
    for k, v in userdb.items():
        if not v:
            raise RuntimeError(f"User {k} has invalid password")
    global USER_DB
    USER_DB = {
        x: {
            "use_history": []
        }
        for x in userdb
    }

    logger.debug("Users:")   
    for k in USER_DB:
        logger.debug(f"  {k}")

    # Instantiate global printer Resource
    printer_config = {
        "idVendor": CONFIG["ESCPOS_USB_IDVENDOR"],
        "idProduct": CONFIG["ESCPOS_USB_IDPRODUCT"],
        "profile": CONFIG["ESCPOS_USB_PROFILE"],
        "use_libusb1": CONFIG.get("ESCPOS_USB_LIBUSB1", False),
    }

    global PRINTER
    PRINTER = directslip.fax.Printer(printer_config)



    if args.test:
        test_print()
        return

    # Create ui
    demo = create_ui(CONFIG)
    demo.launch(
        auth=[(k,v) for k,v in userdb.items()],
        footer_links=["api"],
        server_name=CONFIG["SERVER_ADDRESS"],
        server_port=CONFIG["SERVER_PORT"],
        favicon_path=pathlib.Path(__file__).parent / "assets" / "favicon.ico"
    )


if __name__ == "__main__":
    _main()