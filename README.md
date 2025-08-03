# SST Forkmount

This repo contains the electronic designs and software for [StarSync Trackers](https://starsynctrackers.com/)
computerized forkmount equatorial mounts. It was designed to work with SST hardware but should work with any fork mount
that uses steppers for motors.

## Component Structure

![Diagram image on how the different components work together to make up the mount](structure_diagram.png)

Below it tries to describe

* Computer connects to the mount through Ethernet or Wifi and control the telescope in one of the following ways.
    * A web browser [SST Discovery Tool](https://github.com/bluthen/SSTForkMountDiscovery)
    * software capable of communicating through a LX200 protocol
* Handpad is a device attached through a USB cable
    * It has a GPS moduled embedded inside it that can give the telescope accurate time and location.
    * Has a interface to control the telescope without a computer attached, with goto and manual slew functions.
* Raspberry pi has a controller board (Pi Hat) attached to it and has three main components.
    * Flask API Server - Provides a REST like API to control the telescope
    * React MUI Frontend - web based user interface to communcate with the API Server
    * LX200 Compatible TCPIP Server - An alternative way to control the telescope through a dedicated TCP/IP Port.
* Motor Control Chain
    * Microcontroller (Teensy) - The Raspberry pi has a controller board attached and communicates with it through TTL
      Serial.
    * The Microcontroller (Teensy) - communicates with stepper drivers using SPI Protocol and step/direction protocol.
    * The stepper drivers (TMC5160) - controls the RA/Dec steppers to point the telescope

# Project directory structure

* [electronics](electronics) - Files related to the hardware of: Handpad, serial to ethernet, main controller
    * [enclosures](electronics/enclosures) - Enclosures to house electronics
    * [firmware](electronics/firmware) - Microcontroller firmware
    * [pcb](electronics/pcb) - Schematic and PCB files
* [piside](piside) - Software the run on the Pi.
    * [client_advanced_slew_limits](piside/client_advanced_slew_limits) - Slew limits UI component
    * [client_main](pisiude/client_main) - The Material UI web client
    * [server](piside/server) - Flask API Server

# TODOs

* Improve a test Error modeling
    * Add Star Alignment to handpad that uses the error modeling feature
    * Good prompts for error modeling/alignment to web ui
* Script and instructions to generate object database `ssteq.sqlite`
* More python type-hinting
* Switch from Flask to [FastAPI](https://fastapi.tiangolo.com/)
* Better testing of encoder usage
* Easier pi setup
* Instructions for settings.json for docker usage
* Alt/Az Mode

# Screenshots

Screen shots of the web client.

![Screen shot of web client software running, circle in middle control directions, side vertical slider for speed.](piside/imgs/shot1.png)

![Screen shot of web client software running, a graph with time and altitude of Arcuturus with coordinates listed](piside/imgs/shot2.png)

![Screen shot of web client software running, advanced configuration window showing settings like steps per degrees, backlash, acceleration](./piside/imgs/shot3.png)

![Screen shot of web client software running, setup menu with a set of buttons to different configuration screens](./piside/imgs/shot4.png)

# Related projects

If you are interested in this project, some of these other open source projects might interest you.

* [OneStep](https://github.com/hjd1964/OnStep)
* [AstroEQ](https://www.astroeq.co.uk/)
* [TeenAstro](https://groups.io/g/TeenAstro)