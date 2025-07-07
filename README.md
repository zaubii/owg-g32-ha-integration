# Otto Wilde G32 Grill Integration for Home Assistant

[![hacs_badge](https://img.shields.io/badge/HACS-Default-orange.svg)](https://github.com/hacs/integration)  
![Maintenance](https://img.shields.io/badge/Maintained%3F-Yes-green.svg)

Connect your Otto Wilde G32 Smart Grill to Home Assistant. This custom integration allows you to monitor all temperature zones, meat probes, gas level, and the firebox status of your grill directly within your Home Assistant instance.

---

*   **Smart Connection Control (New in v5.6.0)**  
    This integration can intelligently manage its connection based on the network presence of your grill. If your router or another integration provides a device\_tracker entity that shows when your grill is connected to your Wi-Fi, you can link it to this integration.

_**How it works:**_

*   Automatic Connection: As soon as the assigned device\_tracker shows home, the integration will automatically try to establish a connection. You no longer need to manually toggle the "Connection Enabled" switch.
*   Resource Saving: Before any reconnect attempt (both rapid retries and long-term backoff), the integration checks the tracker's status. If the grill is not home, all connection attempts are paused, saving system resources and avoiding unnecessary network traffic.

_**How to Configure.**_

*   You can set up or change this feature at any time after the initial installation.

1.  Navigate to Settings > Devices & Services.
2.  Find the Otto Wilde G32 Grill integration and click on Configure.
3.  A dialog will appear, listing all your grills. For each grill, you can use the dropdown menu to select a corresponding device\_tracker entity from your Home Assistant instance.
4.  Select the desired tracker for each grill (or leave it blank to disable the feature for that grill) and click Submit.

The changes will take effect immediately.

---

## Features

*   **Smart Connection Control:** (Optional) Automatically manages the connection based on the grill's network presence via a device\_tracker.
*   **Real-time Sensor Data:** Get live updates from your grill via a cloud push connection.
*   **8 Temperature Sensors:**
    *   Four heating zones (`Zone 1` - `Zone 4`).
    *   Four external meat probes (`Probe 1` - `Probe 4`).
*   **Gas Management:**
    *   Monitor the remaining gas in your tank by weight (grams) and percentage.
    *   Sensors for the gas bottle's original capacity and tare weight (from GasBuddy).
    *   Timestamps for when the gas was last installed or consumed.
*   **Liveness Monitoring:** A timestamp sensor shows when the last data packet was received, allowing for robust connection health monitoring and automations.
*   **Status Indicators:** Instantly see if the firebox is open, the light is on, or if the gas is running low.
*   **Multi-Grill Support:** Automatically discovers and sets up all grills associated with your Otto Wilde account.
*   **Robust Connection Management:**
    *   **Two-Stage Retry:** Handles connection losses intelligently. It first tries 5 "rapid retries" to recover from short glitches. If that fails, it switches to a long-term backoff mode.
    *   **Reliable Timeout:** If the grill remains offline, the connection is automatically disabled after 30 minutes in backoff mode to prevent endless retries.
    *   **Connection Switch:** A dedicated switch allows you to manually enable or disable the connection for each grill.
*   **Persistent Diagnostics:** Provides detailed sensors to monitor the integration's internal state. Key counters survive Home Assistant restarts to give a true long-term overview.
*   **Easy Configuration:** Set up everything through the Home Assistant UI.
    
    ## **1\. Important Prerequisites**
    

Before installing this integration, you **must** perform a few crucial steps in the official **Otto Wilde App** on your smartphone. These steps ensure that your grill sends the necessary data to the cloud, which this integration relies on.

1.  **Connect Grill to Wi-Fi:** Ensure your G32 is successfully connected to your local Wi-Fi network via the Otto Wilde app.
2.  **Link to Account:** The grill must be linked to your Otto Wilde user account.
3.  **Set a Nickname (Crucial!):** Give your grill a meaningful nickname in the app (e.g., "My G32"). **This name will be used to create the entity\_ids in Home Assistant.** Changing the name in the app later will also change all entity IDs in Home Assistant!
4.  **Enable "Show in Dashboard":** In the grill's settings within the app, the option **"Show in Dashboard" must be enabled**.
5.  **Set Connection Type to Wi-Fi:** In the grill's settings, the preferred connection type must be set to **"Wi-Fi"** or **"Wi-Fi and Bluetooth"**. If it is set to "Bluetooth" only, the grill will not send data to the cloud, and this integration will not work.

## **2\. How It Works (Architecture)**

This integration uses a **hybrid cloud approach**. It is important to understand that the **Otto Wilde Cloud is always required**. There is no direct, local communication between Home Assistant and the grill.  
The process is as follows:

1.  **Your G32 Grill:** The microcontroller in your grill is connected to your Wi-Fi and continuously pushes its status (as binary packets) to Otto Wilde's central servers.
2.  **Home Assistant Integration (Login):** On startup, this integration authenticates with the Otto Wilde REST API using your credentials. It retrieves a list of your grills and the necessary keys to "subscribe" to the data stream.
3.  **Home Assistant Integration (Data Stream):** After logging in, the integration establishes a persistent TCP connection to the Otto Wilde real-time server (socket.ottowildeapp.com). It then listens for the data packets that your specific grill is sending to the server.

Although the data is not exchanged directly on your local network, this cloud\_push approach provides the benefit of real-time updates without the need for constant polling from the integration.

### **The "Connection Enabled" Switch**

A switch entity named **"Connection Enabled"** is created for each grill. This switch is crucial for the integration's operation:

*   It indicates whether the integration is actively trying to maintain a connection to your grill's data stream.
*   **Important:** If your grill has been offline for more than 30-45 minutes, this switch will automatically turn off to conserve system resources. **You must manually turn it back on** once your grill is powered on and online again to resume receiving data.

## **3\. Installation**

The recommended installation method is via the [Home Assistant Community Store (HACS)](https://hacs.xyz/).

1.  In Home Assistant, go to HACS.
2.  Click on "Integrations", then click the three dots in the top right corner and select "Custom repositories".
3.  Add the repository URL: https://github.com/zaubii/owg-g32-ha-integration
4.  Select "Integration" as the category.
5.  Click "Add". The integration will now appear in your HACS list.
6.  Click "Install" on the "Otto Wilde G32 Grill" card.
7.  Restart Home Assistant.
8.  Go to "Settings > Devices & Services", click "Add Integration", and search for "Otto Wilde G32 Grill".

## **4\. Provided Entities**

The integration creates the following entities for each grill. The entity\_id is based on the nickname you set in the Otto Wilde app.

### **Main Sensors**

| Display Name | Description | Calculation / Formula |
| --- | --- | --- |
| **Zone 1** - **Zone 4** | The current temperature of the four main heating zones in °C. | (hex\[0\] \* 10) + (hex\[1\] / 10.0) |
| **Probe 1** - **Probe 4** | The current temperature of the four external meat probes in °C. | (hex\[0\] \* 10) + (hex\[1\] / 10.0) |
| **Gas Weight** | The net weight of the remaining gas in the tank, measured in grams. | int.from\_bytes(hex, 'big') |
| **Gas Level** | The remaining gas level as a percentage. | int.from\_bytes(hex, 'big') |
| **New Gas Installed** | Timestamp of when a new gas tank was registered in the Gasbuddy. | From REST API |
| **Gas Setup Changed** | Timestamp of when the gas setup was last modified. | From REST API |
| **Gas Consumed** | Timestamp of the last recorded gas consumption event. | From REST API |
| **Firebox** | Indicates if the grill lid (firebox) is open (on) or closed (off). | True if byte is 01 |
| **Light** | Indicates if the grill's internal light is on (on) or off (off). | True if byte is 01 |
| **Gas Low** | A warning that is on when the gas weight drops below 2200g. | True if Gas Weight \< 2200 |

### **Diagnostic & Control Entities**

| Display Name | Description | Calculation / Formula |
| --- | --- | --- |
| **Connection Enabled** | A switch to manually enable or disable the data connection to the grill. Turns off automatically after a 30-minute timeout. | User controlled |
| **API Login Calls** | A persistent counter for the total number of logins to the Otto Wilde API. | Internal counter |
| **API Grills Calls** | A persistent counter for the total number of times grill details were fetched from the API. | Internal counter |
| **TCP Connection Attempts** | A persistent counter for the total number of TCP connection attempts for this grill. | Internal counter |
| **TCP Backoff Counter** | Shows the current number of retries in a backoff sequence after a connection loss. | Internal counter |
| **Next Backoff Attempt** | A timestamp showing when the next scheduled reconnect attempt will occur. | Internal calculation |
| **Raw Hex Dump** | Displays the full, raw 51-byte data packet as a hex string for debugging. (Disabled by default) | Raw data from TCP stream |

## **5\. Data Packet Analysis**

The integration is based on reverse-engineering the 51-byte data packet that the grill sends. Here is the currently known structure, confirmed by the parsing logic in the code.  
_Positions are 0-based. "Chars" refers to the index in the hex string representation._

| Bytes | Chars | Length (Bytes) | Description |
| --- | --- | --- | --- |
| 0-1 | 0-3 | 2 | Packet Header a33a |
| 2-5 | 4-11 | 4 | Grill Serial ID |
| 6-7 | 12-15 | 2 | **Zone 1** Temperature |
| 8-9 | 16-19 | 2 | **Zone 2** Temperature |
| 10-11 | 20-23 | 2 | **Zone 3** Temperature |
| 12-13 | 24-27 | 2 | **Zone 4** Temperature |
| 14-15 | 28-31 | 2 | **Probe 1** Temperature |
| 16-17 | 32-35 | 2 | **Probe 2** Temperature |
| 18-19 | 36-39 | 2 | **Probe 3** Temperature |
| 20-21 | 40-43 | 2 | **Probe 4** Temperature |
| 22-23 | 44-47 | 2 | **Gas Weight** (grams) |
| 24 | 48-49 | 1 | **Lid Status** (01 = open) |
| 25 | 50-51 | 1 | **Light Status** (01 = on) |
| 26-30 | 52-61 | 5 | _Unknown Area 2_ |
| 31 | 62-63 | 1 | **Gas Level** (percent) |
| 32-50 | 64-101 | 19 | _Unknown Area 3 (likely status flags, timers, etc.)_ |

## **6\. Debugging**

If you encounter issues, you can enable debug logging to get more information.

1.  Go to **Settings** > **Devices & Services**.
2.  Find the "Otto Wilde G32 Grill" integration and click the three dots.
3.  Select **Enable debug logging**.
4.  Check the logs at **Settings** > **System** > **Logs**.

Alternatively, add the following to your configuration.yaml:

`logger:`  
  `default: warning`  
  `logs:`  
    `custom_components.otto_wilde_g32: debug`  
  
 

## **Acknowledgements**

This integration would not have been possible without the initialwork done by the community. Special thanks to:

*   fschwarz86/g32
*   ralmoe/g32-docker-client

## **Disclaimer**

This is a third-party integration developed by the community and is not officially developed or supported by Otto Wilde GmbH. Use at your own risk.