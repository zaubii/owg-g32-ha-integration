# **Changelog**

All notable changes to this project will be documented in this file.  
The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/), and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## **\[5.6.0\] \- 2025-07-07**

### **Added**

* **Smart Connection Control via Device Tracker:**  
  * You can now assign a device\_tracker entity to each grill via the integration's "Configure" menu.  
  * If a tracker is assigned, the integration will automatically attempt to connect to the grill as soon as the tracker's state becomes home.

## The reconnect logic (both rapid and backoff) will now check the tracker's state before each attempt. If the device is not home, all reconnect attempts will be paused until it comes back online, saving system resources.

## **\[5.5.3\] \- 2025-07-07**

### **Changed**

* Removed the "G32" prefix from the "Last Data Received" sensor's friendly name to improve consistency with other sensor names.

## **\[5.5.2\] \- 2025-07-07**

### **Fixed**

* **Critical Bug:** Fixed a race condition that caused global diagnostic counters (e.g., API Calls) to be incremented multiple times on startup when more than one grill was configured. The sync logic now ensures global counters are only restored once per session.

## **\[5.5.1\] \- 2025-07-07**

### **Fixed**

* **Critical Bug:** Fixed a recursive loop in the API client that could cause an excessive number of API calls if the access token became invalid. Replaced the recursion with a safe, single-retry mechanism.

## **\[5.5.0\] \- 2025-07-07**

### **Added**

* **New Liveness Sensor:** Added a new timestamp sensor sensor.\[grill\_nickname\]\_last\_data\_received. This sensor updates to the current time whenever a data packet is successfully received from the grill, providing a reliable way to monitor connection health.

## **\[5.4.2\] \- 2025-07-07**

### **Changed**

* The new GasBuddy sensors (Gas Original Capacity and Gas Tara Weight) are now created as standard sensors instead of diagnostic sensors, making them visible by default.

## **\[5.4.1\] \- 2025-07-07**

### **Fixed**

* Corrected an ImportError that prevented the integration from loading. The previously used UnitOfWeight constant was incorrect and has been replaced with the valid UnitOfMass.KILOGRAMS.

## **\[5.4.0\] \- 2025-07-07**

### **Added**

* **New GasBuddy Sensors:** Added two new diagnostic sensors for GasBuddy users:  
  * sensor.\[grill\_nickname\]\_gas\_original\_capacity: Shows the configured capacity of the gas bottle (e.g., 11 kg).  
  * sensor.\[grill\_nickname\]\_gas\_tara\_weight: Shows the configured tare weight (empty weight) of the gas bottle.

## **\[5.3.0\] \- 2025-07-02**

### **Fixed**

* **Diagnostic Sensors Not Updating:** Fixed a critical bug where the API Login Calls and API Grills Calls sensors would not update their state immediately after a call was made.  
* **TCP Counter Not Restoring:** Fixed a bug that prevented the TCP Connection Attempts counter from correctly restoring its value after a Home Assistant restart.

## **\[5.2.0\] \- 2025-07-01**

*(This version included minor non-code changes or was a version bump for release management.)*

## **\[5.1.0\] \- 2025-07-01**

### **Changed**

* **Major Overhaul of Connection Logic:** The entire connection and reconnection mechanism has been rebuilt from the ground up to be more robust and reliable.  
* **Condition for Success:** A connection is now only considered successful after the first data packet ("heartbeat") is received from the grill.  
* **Two-Stage Retry System:** Implemented a rapid retry stage before the long-term backoff mechanism.  
* **Persistent Diagnostic Counters:** The API and TCP diagnostic counters are now persistent and survive Home Assistant restarts.

### **Fixed**

* Fixed a critical bug where the 30-minute timeout logic would never be reached if the grill was offline.

## **\[5.0.1\] \- 2025-07-01**

This version was a transitional release and its changes have been merged into 5.1.0.

## **\[5.0.0\] \- 2025-06-30**

### **⚠️ BREAKING CHANGES**

* **All entity IDs have been renamed** to be fully in English and to follow Home Assistant best practices.  
* The entity binary\_sensor.\*\_lid\_open is now binary\_sensor.\*\_firebox\_open.

### **Fixed**

* **Critical Bug:** Corrected the mapping of temperature sensors. The values for **Grill Zones** and external **Meat Probes** were swapped.

### **Changed**

* **Internationalization:** All display names, services, and entity IDs are now in English.  
* **Entity Naming:** Entity names and IDs have been refined to be more consistent (e.g. lid is now firebox).

## **\[4.3.0\] \- 2025-06-30**

### **Added**

* Custom icons for "Firebox" (mdi:window-opened/mdi:window-closed) and "Light" (mdi:wall-sconce-flat).

## **\[4.2.0\] \- 2025-06-29**

### **Added**

* A master "Connection Active" switch (switch.GRILLNAME\_connection\_active) for each grill.

## **\[4.1.0\] \- 2025-06-29**

### **Added**

* New GasBuddy timestamp sensors for last consumption and last value.

## **\[4.0.0\] \- 2025-06-29**

### **Added**

* **Multi-Grill Support:** The integration now automatically discovers and sets up all grills associated with a single account.  
* Dynamic device creation and naming based on the nickname in the Otto Wilde app.

### **Changed**

* Major code refactoring to handle multiple devices and TCP connections simultaneously.

## **\[3.0.0\] \- 2025-06-29**

### **Changed**

* **PACKET DECRYPTED\!** The position for the gas\_level\_percent sensor was definitively corrected.  
* Fully decoded the logic of the internal countdown timer.

## **\[2.1.0\] \- 2025-06-29**

### **Fixed**

* Corrected the byte position for gas\_level\_percent (intermediate, incorrect finding).

## **\[2.0.0\] \- 2025-06-29**

### **Changed**

* Incorrectly identified the byte position for gas\_level\_percent.

## **\[1.3.0\] \- 2025-06-29**

### **Changed**

* Updated packet parsing function based on initial (incomplete) analysis.

## **\[1.2.1\] \- 2025-06-29**

### **Fixed**

* First attempt to correct byte positions for gas-related sensors.  
* Changed device class for the "Gas Low" warning to PROBLEM.

## **\[1.2.0\] \- 2025-06-29**

### **Added**

* Initial implementation of gas\_level, light, and gas\_low sensors.

## **\[1.1.0\] \- 2025-06-28**

### **Added**

* **Initial Release:** First version of the integration.  
* **Core Functionality:** Login to Otto Wilde Cloud API and establish a TCP connection.  
* **Core Sensors:** 8 Temperature Sensors, Gas Weight, Lid Status, Light Status, and Gas Low Warning.  
* UI Configuration through Home Assistant config flow.