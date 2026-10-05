# Robot projects

This repository contains independent programs for LEGO MINDSTORMS robots.

| Robot | Project |
| --- | --- |
| [R3ptar](R3ptar/) | Autonomous exploration, dancing, and beginner-friendly programs for the R3ptar robot |
| [Robodoz3r](Robodoz3r/) | Autonomous bulldozer with blade salutes, obstacle escapes, reversing beeps, and disco breaks |

Each robot's code, tests, and robot-specific instructions live in its folder. The VS Code workspace configuration is shared at the repository root.

## Shared EV3 setup

Both projects use the same setup:

- A built LEGO MINDSTORMS EV3 robot and an EV3 Brick running **EV3 MicroPython 2.0**
- A microSD card and mini-USB cable for the EV3 setup
- Visual Studio Code with the **LEGO MINDSTORMS EV3 MicroPython** extension
- A clear, level floor with room for the robot to move

Follow the official [Pybricks EV3 installation guide](https://pybricks.com/install/mindstorms-ev3/installation/) to prepare the microSD card, boot the brick, and install the VS Code extension.

Clone this repository and open its top-level folder in VS Code so that the shared `.vscode/launch.json` is available:

```bash
git clone https://github.com/YudakovAlex/fun_r3ptar.git
cd fun_r3ptar
code .
```

## Connect with the ev3dev Device Browser

The LEGO extension includes the **ev3dev Device Browser**, shown in VS Code's Explorer sidebar. It connects to the brick over SSH to browse files, transfer your project, and run programs remotely. USB and Bluetooth tethering provide network connections to the brick; Bluetooth pairing alone is not enough. See the [ev3dev networking guide](https://www.ev3dev.org/docs/networking/) for connection setup.

1. Turn on the EV3 Brick and establish a network connection to your computer, for example with the mini-USB cable or Bluetooth tethering.
2. In **EV3DEV DEVICE BROWSER**, click **Click here to connect to a device** and select your brick.
3. If the brick is missing from the list, choose **I don't see my device** and enter the brick's IP address shown on its screen.
4. Once connected, expand the device to browse its files. Right-click the device to open an SSH terminal when needed.

**VPN troubleshooting:** a VPN may block device discovery or the connection to the brick **even over Bluetooth**, because Bluetooth tethering still carries network traffic. If the brick cannot be found or the connection times out, disconnect the VPN or enable its local-network access setting, then reconnect in the device browser. Using the brick's IP address can help when discovery fails, but it cannot bypass a VPN that blocks local traffic.

The [device browser documentation](https://github.com/ev3dev/vscode-ev3dev-browser) and [Pybricks running-programs guide](https://pybricks.com/install/mindstorms-ev3/running-programs/) explain browsing, downloading, and launching programs.

## Download and run

Check the robot's wiring and starting position in its README before running it:

- [R3ptar wiring and positioning](R3ptar/README.md#plug-in-the-creature)
- [Robodoz3r wiring and setup](Robodoz3r/README.md#wiring-and-setup)

In VS Code's **Run and Debug** menu, select **Download and Run** for `R3ptar/main.py` or **Robodoz3r: Download and Run** for `Robodoz3r/main.py`, then press `F5`. The project folder is copied to the brick and the selected program runs there.

To run R3ptar's `dance.py` or `basic.py`, change the R3ptar configuration's `program` in [`.vscode/launch.json`](.vscode/launch.json) to end in `R3ptar/dance.py` or `R3ptar/basic.py`, then press `F5` again.
