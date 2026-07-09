import asyncio
import logging
import tomllib
import pathlib
import io

import PIL

import microdot
import microdot.multipart
import rich

#import directslip
#import directslip.fax
import directslip.printer

# ROOT
root_router = microdot.Microdot()

#@root_router.route('/favicon.ico')
#def favicon(request):
#    return microdot.send_file('server_api/favicon.ico', content_type='image/x-icon')

@root_router.route('')
def root(request):
  """Root path"""
  return {
    "status": True,
    "version": "1.0"
  }

@root_router.route('routes')
async def list_routes(request):
    """Dynamically maps and displays all endpoints, methods, and descriptions."""
    routes_info = []
    app = request.app
    for route in app.url_map:
        route_methods, route_pattern, route_func,d,e = route
        # Extract metadata from the URLPattern object
        routes_info.append({
            "path": route_pattern.url_pattern,
            "methods": "-".join(route_methods),
            "description": route_func.__doc__.strip() if route_func.__doc__ else None
        })
    #rich.print(routes_info)
    return {"routes": routes_info}

# API 
api_router = microdot.Microdot()
@api_router.before_request
def preprocess_request(request):
    if not request.app.printer.is_printer_ok():
        return {"error": "Printer Offline"}, 503

@api_router.route('/status')
async def status(request):
    """Gives Printer Status"""
    return {
      "status": request.app.printer.status_str()
    }

# TODO ALWAYS MAKE SURE its online before sending anything
@api_router.route('/test')
async def test(request):
    """Perform a test print"""
    request.app.printer.print_test()
    return {"status": "OK"}, 200

@api_router.post('/text')
async def text(request):
    """Perform a test print"""
    #rich.print(request.json)
    if not isinstance(request.json, dict):
    	return {"error": "Bad Request", "message": "Bad JSON Body"}, 400
    text = request.json.get("text")
    if not isinstance(text, str):
        return {"error": "Bad Request", "message": "Bad Body"}, 400
    if not text:
        return {"error": "Bad Request", "message": "Bad Body text"}, 400
    request.app.printer.print_text(text)
    return {"status": "OK"}, 200

@api_router.post('/image')
@microdot.multipart.with_form_data
async def upload_image(request):
    """Print an Image and cut"""
    # Microdot handles multipart form data via request.files
    #rich.print(request.body)
    #rich.print(request.json, request.form, request.files)
    #rich.print(request.form.get('image'))
    if request.files is None or not 'image' in request.files:
        return Response('No image provided', status_code=400)
    file = request.files["image"]

    image_load = PIL.Image.open(io.BytesIO(await file.read()))
    request.app.printer.print_image(image_load)
    # TODO CLOSE OR SEND ONLY THE STREAM

    return {'status': 'success', 'message': f'Received {file.filename}'}

def cleanup():
  print("cleanup")


# Logging
logger = logging.getLogger("directslip")

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

def get_config():
  config = read_config(pathlib.Path("config.toml"))
  config = read_config(pathlib.Path("defaults.toml")) | config
  return config


async def main():
    microdot.Request.max_content_length = 25*1024*1024
    microdot.Request.max_body_length = 25*1024*1024

    # APP CREATION
    app = microdot.Microdot()
    root_router.mount(api_router, url_prefix='api')
    app.mount(root_router, url_prefix='/')

    # CONFIG
    app.config = get_config()

    # STATE
    print(f"Initializing printer:")
    printer_config = {
        "idVendor": app.config["ESCPOS_USB_IDVENDOR"],
        "idProduct": app.config["ESCPOS_USB_IDPRODUCT"],
        "profile": app.config["ESCPOS_USB_PROFILE"],
        "use_libusb1": app.config.get("ESCPOS_USB_LIBUSB1", False),
    }
    rich.print(printer_config)
    app.printer = None
    #app.printer = directslip.fax.Printer(printer_config)
    app.printer = directslip.printer.Printer(printer_config)
    app.printer.is_printer_ok()  # Forces some init ...
    #bg_task ...
    server = asyncio.create_task(app.start_server(host='0.0.0.0', port=6969, debug=True))

    try:
        # Keep running until the server task finishes or gets canceled
        await server
    except asyncio.CancelledError:
        print("Server cancelled")
    # 3. CLEANUP: Ensure resources are released when exiting
    finally:
        cleanup()
        #bg_task.cancel()
        # Await server cleanup if necessary
        await server

    # Cleanup

if __name__ == "__main__":
  asyncio.run(main())

