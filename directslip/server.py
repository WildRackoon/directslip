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


def send_msg(msg, image, request: gr.Request):  # name, image
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
        fax = directslip.fax.Fax(user_name, msg, image, force_portrait=False)  # Force protrait
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
    return None, None

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
        # with gr.Blocks(fill_height=True):
        input_msg = gr.Textbox(label="Message", placeholder="Fax Message", lines=5)
        input_img = gr.Image(label="Image Document", height=200, sources=['upload', 'clipboard'])

        # output_box = gr.Text(visible=False)

        btn_send = gr.Button("Send")
        btn_send.click(
            fn=send_msg,
            inputs=[
                input_msg,
                input_img
            ],
            # outputs=[output_box],
            api_name="send",
        ).success(
            clear_inputs, outputs=[input_msg, input_img], api_visibility="private"
        )

    return demo


def read_config(config_path: pathlib.Path) -> dict | None:
    try:
        with config_path.open("rb") as fh:
            return tomllib.load(fh)
    except tomllib.TOMLDecodeError as exc:
        logger.critical("Configuration file is invalid: `{config_path}`")
        logger.error(exc, exc_info=True)
        return None


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
    args = parser.parse_args()

    # Check Arguments
    config_path = pathlib.Path(args.config or "config.toml")
    if not config_path.is_file():
        logger.error(f"Config file does not exists: `{config_path}`")
        return

    # Read config
    # config = read_config(pathlib.Path("defaults.toml"))
    
    config = read_config(config_path)
    if config is None:
        return
    config = read_config(pathlib.Path("defaults.toml")) | config

    # Set Log Level
    logger.setLevel(getattr(logging, config["LOG_LEVEL"]))

    # Dump Config
    logger.debug("Config:")
    for k,v in config.items():
        logger.debug(f"  {k:32} {v}")

    # Dump Users
    userdb = read_config(pathlib.Path("userdb.toml"))
    logger.debug("Users:")
    for k in userdb:
        logger.debug(f"  {k}")

    # Instantiate global printer Resource
    global CONFIG
    CONFIG = config

    global PRINTER
    PRINTER = directslip.fax.Printer()

    global USER_DB
    USER_DB = {
        x: {
            "use_history": []
        }
        for x in userdb
    }

    # Create ui
    demo = create_ui(config)
    demo.launch(
        auth=[(k,v) for k,v in userdb.items()],
        footer_links=["api"],
        server_name=config["SERVER_ADDRESS"],
        server_port=config["SERVER_PORT"],
        favicon_path=pathlib.Path(__file__).parent / "assets" / "favicon.ico"
    )


if __name__ == "__main__":
    _main()