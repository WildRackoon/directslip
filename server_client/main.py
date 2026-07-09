import asyncio
import logging
import tomllib
import pathlib

import rich
import gradio as gr

import rich
import urllib
import urllib.request
import json

import functools


# CONFIG
BASE_URL="http://192.168.1.13:6969"

# REQUESTION

def send_request(url, payload, method="POST"):
    try:
      req = urllib.request.Request(
          url,
          data=json.dumps(payload).encode('utf-8'),
          headers={
              'Content-Type': 'application/json',
              #'Accept': 'application/json',
              #'User-Agent': 'Embedded-Pi-Zero-Client'
          },
          method=method
      )
      with urllib.request.urlopen(req, timeout=3) as response:
          return json.loads(response.read().decode('utf-8'))
    except Exception as exc:
        rich.print(exc)

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
def process_image(input_img, size):
    if input_img is None:
        return "Please upload an image first!"
    
    # Example logic based on the selected size
    width, height = input_img.size
    
    factor_map={
        i: 1.0/float(i)
        for i in (1, 2, 3)
    }
    factor=factor_map[int(size)]
    rich.print(f"Must print {factor}")

    # res = send_request(f"{BASE_URL}/api/test", None, method="GET")
    # res = send_request(f"{BASE_URL}/api/text", {"text": "Hello world"})
    # rich.print(res)

    gr.Success("Success")

def process_image_change(image_path):
    if image_path is None:
        return ""
    return f"Size: {image_path.size}"


def main():
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
    