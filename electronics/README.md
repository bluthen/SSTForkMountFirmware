# SST Electronics Hardware

## PiHat/SSTFork Stepper Micro

This is the electronics that take communication from the Pi and control the stepper motors.

## Handpad

This is the electronics of the handpad. A handheld device, with a display, to control the telescope mount.

## Serial to Ethernet

This is a small device that creates a serial port on the host computer and sends back and forth all communication on the
serial port to a IP_ADDRESS:Port through Ethernet.

This could be handy for older software that can only communicate with LX200 Protocol through a serial port.

**Computer** <-USB Serial-> **serial_to_ethernet** <-Ethernet-> **Device/Fork Mount**

# Directroy Structure

See each section for more information.

* [enclosures](enclosures) - Enclosure to house electronics
* [firmware](firmware) - Microcontroller firmware files
* [pcb](pcb) - Schematic and PCB for electronics