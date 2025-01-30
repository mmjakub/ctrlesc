#!/usr/bin/env python3
from select import select
from time import perf_counter

from evdev import UInput, InputDevice, list_devices, ecodes as ec

KB = (0x25a7, 0xfa70)
MOUSE = (0x3299, 0x4e52)
DELAY = .15

LEFTCTRL = 0x700e0
ESC = 0x70029

def get_kb_mouse():
    devices = {}
    for path in list_devices():
        dev = InputDevice(path)
        info = (dev.info.vendor, dev.info.product)
        if info not in devices:
            devices[info] = dev
    return devices[KB], devices[MOUSE]

def ctrl(ctrl_down_event, ui, kb, mouse):
    key_event = []

    def flush_events():
        for buf in (ctrl_down_event, key_event):
            for e in buf:
                ui.write_event(e)
            ui.syn()

    td = 0
    t0 = perf_counter()
    while td < DELAY:
        r, _, _ = select([kb, mouse], [], [], DELAY - td)
        if not r:
            flush_events()
            break
        for dev in r:
            ev = dev.read_one()
            if dev is kb:
                # scan events
                if ev.type == ec.EV_MSC and ev.code == ec.MSC_SCAN:
                    if ev.value == LEFTCTRL:
                        ui.write(ec.EV_MSC, ec.MSC_SCAN, ESC)
                        ui.write(ec.EV_KEY, ec.KEY_ESC, 1)
                        ui.syn()
                        ui.write(ec.EV_MSC, ec.MSC_SCAN, ESC)
                        ui.write(ec.EV_KEY, ec.KEY_ESC, 0)
                        ui.syn()
                        return
                    else:
                        key_event.append(ev)
                        key_event.append(kb.read_one())
                        flush_events()
                        return
                elif ev.type == ec.EV_KEY and ev.code == ec.KEY_LEFTCTRL and ev.value == 2:
                    key_event.append(ev)
                    flush_events()
                    return
            # mouse events
            else:
                # mouse button down or wheel
                if ev.type == ec.EV_KEY and ev.value == 1 or ev.code == ec.REL_WHEEL:
                    flush_events()
                    return
        td = perf_counter() - t0

def main():
    kb, mouse = get_kb_mouse()
    with UInput.from_device(kb, name='my-keyboard') as ui, kb.grab_context():
        buf = []
        for ev in kb.read_loop():
            if buf:
                buf.append(ev)
                ctrl(buf, ui, kb, mouse)
                buf = []
            elif ev.type == ec.EV_MSC and ev.code == ec.MSC_SCAN and ev.value == LEFTCTRL:
                buf.append(ev)
                continue
            elif ev.code == ec.KEY_PAUSE and ev.value == 1:
                print('exit')
                return
            else:
                ui.write_event(ev)
if __name__ == '__main__':
    main()

