import asyncio
import logging
import tomllib
import pathlib
import io

import rich
import rich.traceback
import gradio as gr
import PIL

import rich
import requests
import json

import functools


# CONFIG
BASE_URL="http://192.168.1.13:6969"


# IAMGE UTILS

# TODO SOMEWHERE ELSE
def pre_process_image(img, target_size=512):
    """May rotate and resize"""
    width, height = img.size
    if height < width:
        img = img.rotate(90, expand=True)
        width, height = img.size  # Update dimensions after rotation
    if width > target_size:
        scale_factor = target_size / width
        new_width = target_size
        new_height = int(height * scale_factor)
        img = img.resize((new_width, new_height), PIL.Image.Resampling.LANCZOS)
    return img

# REQUEST
def send_request(url, json=None, data=None, method="POST", files=None):
    # try:
    res = requests.request(
        method,
        url,
        json=json,  # TODO need data for forms ?
        data=data,
        # headers={
        #     #'Accept': 'application/json',
        #     #'User-Agent': 'Embedded-Pi-Zero-Client'
        # },
        files=files
    )
    if not res.ok:
        try:
            err_json = res.json()
        except Exception:
            err_json = None
        rich.print("ERROR:", res.status_code, res.text, err_json)  # TODO UNSAFE res.json()

    return res

    # except Exception as exc:
    #     rich.print("Exception in req:", exc)

# UTILS
def _clear_inputs(*, number:int):
    # error if 0
    if number == 1:
        return None
    else:
        return (None,)*number

def func_clear_input(number:int):
    return functools.partial(_clear_inputs, number=1)


# GRADIO
def process_image(input_img: PIL.Image.Image, size):
    if input_img is None:
        return "Please upload an image first!"

    input_img = pre_process_image(input_img)

    # Example logic based on the selected size
    width, height = input_img.size
    
    factor_map={
        i: 1.0/float(i)
        for i in (1, 2, 3)
    }
    factor=factor_map[int(size)]
    rich.print(f"Must print {factor}")

    # 1. Convert the PIL Image into bytes in memory
    byte_arr = io.BytesIO()
    input_img.save(byte_arr, format='PNG')
    byte_arr.seek(0)

    res = send_request(
        f"{BASE_URL}/api/image",
        data={"metadata": "dummyshit"},
        files={
            'image': ('image.png', byte_arr, 'image/png')  # TODO NAME
        }
    )
    rich.print(res.json())



    gr.Success("Success")

def process_image_change(image_path):
    if image_path is None:
        return ""
    return f"Size: {image_path.size}"






# TODO TEST AND TEXT
def req_test():
    res = send_request(f"{BASE_URL}/api/test", json=None, method="GET")
    rich.print(res)
    
def req_text(text):
    res = send_request(f"{BASE_URL}/api/text", json={"text": text})
    rich.print(res)


def main():

    # RICH DEBUG
    rich.traceback.install(show_locals=True)

    def get_navbar():
        pass
        navbar = gr.Navbar(
            visible=True,
            main_page_name="Fax",
            # value=[("About", "https://example.com/about")]
        )

    with gr.Blocks() as demo:
        get_navbar()
        gr.Markdown("# Menu")

    with demo.route("Images") as greeter_demo:
        get_navbar()
        gr.Markdown("# Images")

        # with gr.Row():
        # with gr.Column():
        # Image Input
        with gr.Group():
            input_img = gr.Image(label="Image", height=200, sources=['upload', 'webcam', 'clipboard'], type="pil", image_mode="L")
            input_status = gr.Textbox(label="ImageStatus", interactive=False, show_label=False, container=False, lines=3)

        # Exclusive Size Selector (Radio buttons)
        # with gr.Row():
        size_selector = gr.Radio(
            choices=["1", "2", "3"], 
            value="1", 
            label="Select Output Size"
        )


        input_img.change(
            fn=process_image_change,
            inputs=input_img,
            outputs=[input_status] # COULD AUTO CHOOSE size_selector
        )

        # Send Button
        send_btn = gr.Button("Send", variant="primary")
                

        # 3. Define the click event logic
        send_btn.click(
            fn=process_image,
            inputs=[input_img, size_selector],
        ).success(
            func_clear_input(1),
            inputs=None,
            outputs=[input_img],
            api_visibility="private"  # TODO MORE THAN PRIVATE JUST REMOVE
        )


    css="""
    body > gradio-app > div > div > nav{justify-content: flex-start !important;}
    footer{display:none !important;}
    """
    demo.launch(css=css)  # 

if __name__ == "__main__":
    main()
    