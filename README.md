# DP-Mass-Upgreader
This script provides the ability to upgrade multiple DPs at once.

## How the script works:
-	The script will read an excel file containing all the necessary information, DP IP, platform, version, image filename.
-	The script will generate upgrade passwords for all devices automatically, devices must be under support contract.
-	The script will start the upgrade process with a concurrency between 1-5, meaning 1-5 DPs can be upgraded in parallel.
-	The script will monitor the upgrade status of each device, if there is an error it will print it with the reason.
-	The script will print a summary of Success/Failure for each DP.

## Prerequisites:
1.	Python3 installed on the client with the following modules:  
  -	Pandas  
  -	requests  
  -	urllib3  
2.	The client running the script must be connected to the internet.


## Usage:
1.	python3 dp_mass_upgrader.py <Vision-IP> <Vision-user> <Vision-pass> <Excel-filename> <1-5>
  -	Vision-IP: IP of the Vision that manages the DPs
  -	Vision-user: Vision login username
  -	Vision-pass: Vision login password
  -	Excel-filename: Name of the excel file with the information
  -	<1-5>: Number of simultaneous upgrades
2. The folder containing the script should also contain the following:
  -	Excel file with all the relevant information: IP, platform, version, image filename
  -	The image file used for the upgrade
3.  Excel formatting notes: 
  -	The platform name in the Excel file must be exactly as it appears in the ‘Supported Platform’ column of the Excel file
  -	The version number in the Excel file must be in the format of x.x.x.x for example: 8.30.0.0, 8.26.2.0 etc.
  -	A template Excel file can be found in the repository


## Example of running the script from a Linux server:

$ python3 dp_mass_upgrader.py 10.10.10.10 radware radware example.xlsx 3  

Fetching all upgrade data...  
Starting bulk upgrade with 3 workers  
DP 10.213.51.213: locked successfully  
DP 10.213.51.213: starting the upgrade process with version DefensePro_VA_v8-26-0-0-b129_Upgrade_VMware.tgz  
DP 10.213.51.212: locked successfully  
DP 10.213.51.211: locked successfully  
DP 10.213.51.211: starting the upgrade process with version DefensePro_VA_v8-26-0-0-b129_Upgrade_VMware.tgz  
DP 10.213.51.212: starting the upgrade process with version DefensePro_VA_v8-26-0-0-b129_Upgrade_VMware.tgz  
DP 10.213.51.213: upload completed, monitoring upgrade status  
DP 10.213.51.212: upload completed, monitoring upgrade status  
DP 10.213.51.211: upload completed, monitoring upgrade status  
DP 10.213.51.211: upgrade status "Activating Software"  
DP 10.213.51.212: upgrade status "Activating Software"  
DP 10.213.51.213: upgrade status "Activating Software"  
DP 10.213.51.211: upgrade successful  
DP 10.213.51.212: upgrade successful  
DP 10.213.51.213: upgrade successful  
Bulk upgrade finished...  
------Upgrade Summary------  
DP 10.213.51.211: upgrade process completed successfully  
DP 10.213.51.212: upgrade process completed successfully  
DP 10.213.51.213: upgrade process completed successfully  
  
  
