import asyncio
import logging
import tomllib
import pathlib

import rich
import gradio as gr
import random
import time

import functools

def process_image(input_img, size):
    if input_img is None:
        return "Please upload an image first!"
    
    # Example logic based on the selected size
    width, height = input_img.size
    
    factor_map={
        i: 1.0/float(i)
        for i in (1, 3, 9)
    }
    factor=factor_map[int(size)]
    rich.print(f"Must print {factor}")

# UTILS
def _clear_inputs(*, number:int):
    # error if 0
    if number == 1:
        return None
    else:
        return (None,)*number

def func_clear_input(number:int):
    return functools.partial(_clear_inputs, number=1)


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

        with gr.Row():
            with gr.Column():
                # Image Input
                input_img = gr.Image(label="Image", height=200, sources=['upload', 'clipboard'], type="pil", image_mode="L")
                
                # Exclusive Size Selector (Radio buttons)
                size_selector = gr.Radio(
                    choices=["1", "4", "9"], 
                    value="1", 
                    label="Select Output Size"
                )
                
                # Send Button
                send_btn = gr.Button("Send", variant="primary")
                

        # 3. Define the click event logic
        send_btn.click(
            fn=process_image,
            inputs=[input_img, size_selector],
        ).success(
            func_clear_input,
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
    