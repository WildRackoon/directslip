# Direct Slip 📨🖨️🧾🩲

> Direct Slip and its Direct-To-Slip technology, is where retro vibes and modern innovation really meet, by letting people slide into my slips in a way that is convenient, fun and addictive.
>
> For me, Instant Slipping is simply the best way to get in touch.
>
> — *Collin Ducraques*

---

The idea is simple:

Use a thermal receipt printer like a [Fax machine](https://en.wikipedia.org/wiki/Fax), allowing users to send short text / image messages for printing on paper slips.

- Leverages [python-escpos](https://github.com/python-escpos/python-escpos) supported devices
- Synchronous server API to receive messages: no inbox.
- Limited features for message formats (wrapped / non-wrapped text, Images...)
- Minimal security: Auth management and request rate limiting 

## Potential future improvements
- Lighter server deployment (API only, Single-board computer framework like MicroPython)
- Home Assistant / Tasmota integration
- Mailbox based printing setup (easy docker mailbox + fetchmail daemon)
- Differente Server / client setup.
- Lightweight contacts management solution

## Install
- Get Python 3.12
- Install requirements.txt
- Manage config.toml
- python -m directslip.server

# Reference
https://support.epson.net/setupnavi/?PINF=menu&MKN=TM-T88V
https://files.support.epson.com/pdf/pos/bulk/tm-t88v_trg_en_revf.pdf