# PiSide - Software that runs on the Pi

![Screen shot of web client software running, circle in middle control directions, side vertical slider for speed.](./imgs/shot1.png)

![Screen shot of web client software running, a graph with time and altitude of Arcuturus with coordinates listed](./imgs/shot2.png)

![Screen shot of web client software running, advanced configuration window showing settings like steps per degrees, backlash, acceleration](./imgs/shot3.png)

![Screen shot of web client software running, setup menu with a set of buttons to different configuration screens](./imgs/shot4.png)

# Docker compose

You can run the software in docker with a simulated microcontroller board. If 

```bash
docker compose build
docker compose up
```

Open browser to: [http://localhost:5001](http://localhost:5001)

# Directory structure

* [server](server) - API Server
* [client_main](client_main) - Material UI based web client
* [client_advanced_slew_limits](client_advanced_slew_limits) - A web interface sub app to set slew limits written in
  jquery
* [setup](setup) - Setup documentation and files