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
DRY_RUN=False

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


def mosaic(input_img, grid_size: int):
    """Create a grid of same size of input image, with images scaled down by grid_size"""
    if grid_size == 1:
        return input_img
    if grid_size <=0:
        raise RuntimeError(f"mosaic: grid_size cannot be negative or zero")
    
    mosaic = PIL.Image.new(input_img.mode, input_img.size)

    width, height = input_img.size
    tile_width, tile_height = width // grid_size, height // grid_size
    tile = input_img.resize((tile_width, tile_height), PIL.Image.Resampling.LANCZOS)

    for row in range(grid_size):
        for col in range(grid_size):
            # Calculate coordinates based on the smaller tile size
            x = col * tile_width
            y = row * tile_height
            mosaic.paste(tile, (x, y))

    return mosaic

def imgs_scale_up(input_img, scale_up: int):
    """Create N images to scale the whole thing up by `scale_up`"""
    if scale_up <=0:
        raise RuntimeError(f"imgs_scale_up: scale_up cannot be negative or zero")

    _width, height = input_img.size  # TODO INCHALLAH ITS 512 man
    new_width, new_height = 512 * scale_up, height * scale_up
    # scaled_img = input_img.resize((new_width, new_height), PIL.Image.Resampling.LANCZOS)

    slice_width_source = 512 / scale_up # The exact width of each slice on the original image

    return [
        input_img.crop(
            (i * slice_width_source, 0, (i + 1) * slice_width_source, height)  # l t r b
        ).resize((512, new_height), PIL.Image.Resampling.LANCZOS)
        for i in range(scale_up)
    ]



# REQUEST
def send_request(url, json=None, data=None, method="POST", files=None) -> dict | None:
    if DRY_RUN:
        res = {
            "json": json,
            "data": data,
            "method": method,
            "files": files,
        }
        return {"dry_run": res}

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

    try:
        res_json = res.json()
    except Exception:
        res_json = None

    if not res.ok:
        rich.print("ERROR:", res.status_code, res.text, res_json)

    return {
        "status": res.status_code,
        "json": res_json,
        "text": res.text,
    }

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



def pil_to_array(img: PIL.Image.Image):
    byte_arr = io.BytesIO()
    img.save(byte_arr, format='PNG')
    byte_arr.seek(0)
    return byte_arr

# GRADIO
def process_image(input_imgs_tuples: PIL.Image.Image):
    input_imgs = [x[0] for x in input_imgs_tuples]
    if not input_imgs:
        return "No images to process"

    # TODO ONLY WHEN USING ACTUAL INPUT, MAYBE DO A CHECK HERE ANYWAY
    # input_img = pre_process_image(input_img)
    # width, height = input_img.size

    # Convert the PIL Image into bytes in memory
    for input_img in input_imgs:
        files = {
            'image': ('image.png', pil_to_array(input_img), 'image/png')  # TODO NAME
        }

        res = send_request(
            f"{BASE_URL}/api/image",
            data={"metadata": "dummyshit"},
            files=files
        )
        rich.print(res)

    gr.Success("Success")

def process_image_change(image_input, *args):
    grid_size_str = args[0]  # TODO ALREADY AN INT
    grid_size=int(grid_size_str)

    if image_input is None:
        return "", None, []

    # Rotate and scale 512xH
    out_preview = pre_process_image(image_input)
    out_images=[out_preview]

    if grid_size < 1:
        out_preview = mosaic(out_preview, -grid_size)
        out_images = [out_preview]
    if grid_size > 1:
        print(f"TODO SCALE UP")
        out_images = imgs_scale_up(out_preview, grid_size)
    else:
        pass  # nothing

    rich.print(out_images)
    rich.print(
        [x.size for x in out_images]
    )

    return f"Size: {image_input.size}", out_preview, out_images






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
            with gr.Row():
                input_img = gr.Image(label="Image", height=300, sources=['upload', 'webcam', 'clipboard'], type="pil", image_mode="L")
                # TODO THE PREVIEW CAN GO
                img_preview = gr.Image(label="Image Preview", height=300, interactive=False, type="pil", image_mode="L")
                img_previews = gr.Gallery(label="Images Preview", height=300, interactive=False, type="pil", columns=8, rows=4)

            input_status = gr.Textbox(label="ImageStatus", interactive=False, show_label=False, container=False, lines=3)

        # Exclusive Size Selector (Radio buttons)
        # with gr.Row():
        input_widgets = {
            "size_selector": gr.Radio(
                choices=[-4,-3,-2,1,2] , 
                value=1, 
                label="Select Output Size",

            )
        }

        # Changes to Image or inputs
        preview_inputs_list = [input_img, *input_widgets.values()]
        preview_outputs_list = [input_status, img_preview, img_previews]
        input_img.change(
            fn=process_image_change,
            inputs=preview_inputs_list,
            outputs=preview_outputs_list
        )
        for input_widget in input_widgets.values():
                input_widget.change(
                    fn=process_image_change,
                    inputs=preview_inputs_list,
                    outputs=preview_outputs_list
                )

        # Send Button
        send_btn = gr.Button("Send", variant="primary")
                

        # 3. Define the click event logic
        send_btn.click(
            fn=process_image,
            # inputs=[input_img, *input_widgets.values()],  # TODO can be a set => means it will give us a **kwargs dict in return
            inputs=[img_previews],  # TODO can be a set => means it will give us a **kwargs dict in return
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
    