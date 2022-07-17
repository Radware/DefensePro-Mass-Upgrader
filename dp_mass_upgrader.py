from requests import Session, packages
import requests
import pandas as pd
import queue
import time
import sys 
import os
import threading
from urllib3.exceptions import InsecureRequestWarning

# Suppress only the single warning from urllib3 needed.
packages.urllib3.disable_warnings(category=InsecureRequestWarning)

# Excel Global Variables
IP_COL = 0
PLATFORM_COL = 1
VERSION_COL = 2
IMAGE_COL = 3

stopping = threading.Event()

class Vision:

	def __init__(self, ip, username, password):
		self.ip = ip
		self.login_data = {"username": username, "password": password}
		self.base_url = "https://" + ip
		self.sess = Session()
		
		self.login()
		
	def login(self):
		login_url = self.base_url + '/mgmt/system/user/login'
		self.sess.headers.update({"Content-Type": "application/json"})
		r = self.sess.post(url=login_url, json=self.login_data, verify=False)
		response = r.json()

		if response['status'] == 'ok':
			self.sess.headers.update({"JSESSIONID": response['jsessionid']})
			self.sess.headers.pop("Content-Type")
			# print("Vision loging successful")
			
		else:
			print(f"Vision login error: {r.text}")
			exit(0)

	def lock_device(self, dp):
		url = self.base_url + f"/mgmt/system/config/tree/device/byip/{dp}/lock"
		r = self.sess.post(url, verify=False)
		if r.status_code == 200:
			print(f"DP {dp}: locked successfully")
			return True
		else:
			print(f"DP {dp}: lock failuer")
			return False

	def get_device_mac(self, dp):
		url = self.base_url + f"/mgmt/device/byip/{dp}/config?prop=rsWSDSysBaseMACAddress"
		r = self.sess.get(url)
		r = r.json()
		if 'rsWSDSysBaseMACAddress' not in r:
			print(f'DP {dp}: error {r}')
			print(f'DP {dp}: could not get mac address from Vision')
			print('Exiting...')
			exit(1)
		mac = r['rsWSDSysBaseMACAddress']
		return mac.replace(':', '')

	def get_file_size(self, platform, version):
		url = 'https://portals.radware.com/Api/InstallBase/GetSoftwareImages'
		v_s = version.split('.')[1]
		v_r = version.replace('.','-')
		data = {"Path":f"/Customer/Home/Downloads/Application-Network-Security/DefensePro/8-x/8-{v_s}/{v_r}/%","Platform":platform}
		r = requests.post(url, json=data)
		r = r.json()
		for file in r:
			if file['ImageType'] == 'Software Upgrade':
				return str(int(file['Size']))

		print(f'Error: could not get the correct file size for the upgrade, {data}')
		print('Exiting...')
		exit(1)

	def get_upgrade_password(self, mac, filesize):
		url = 'http://services.radware.com/api/securityupdate/v1/password'
		data = {'mac':mac, 'filesize':filesize}
		r = requests.post(url, json=data)
		r = r.json()

		if r['status'] == 'Success':
			return r['data']['password']

		print(f'Error: {r["message"]} {data}')
		print('Exiting...')
		exit(1)
		
	def upgrade_dp(self, dp, file, password):
		url = self.base_url + f'/mgmt/device/byip/{dp}/config/updatesoftware?enableNewVersion=1&password={password}&genpassauto=false&fileName={file}'
		try:
			form = {'Filedata': open(file,'rb')}
		except FileNotFoundError:
			print(f'Error: file not found {file}')
			os._exit(1)

		print(f'DP {dp}: starting the upgrade process with version {file}')
		r = self.sess.post(url=url, files=form, verify=False)
		r = r.json()

		if 'status' in r and r['status'] == 'ok':
			print(f'DP {dp}: upload completed, monitoring upgrade status')
			return r['location']
		
		print(f'DP {dp}: upgrade failed with the following error {r}')
		return ''

	def monitor_upgrade(self, dp, location):
		url = self.base_url + '/mgmt' + location
		r = self.sess.get(url=url, verify=False)
		r = r.json()

		return r

class ExcelParser:

	def __init__(self, file):
		self.file = file
		self.worksheet = pd.read_excel(self.file, usecols = 'A:D', keep_default_na=False)

	def parse(self, dp_info_dic):
		self.worksheet.head()
		for index, row in self.worksheet.iterrows():
			# Making sure we do not add empty lines
			if row[IP_COL]:
				dp_info_dic[row[IP_COL]] = {'platform':row[PLATFORM_COL], 'version':row[VERSION_COL], 'image':row[IMAGE_COL]}

def build_dp_database(e, v, dp_info_dic):
	# Parsing the excel file 
	e.parse(dp_info_dic)

	# Updating dp_info_dic with additional info
	for dp, data in dp_info_dic.items():
		mac = v.get_device_mac(dp)
		filesize = v.get_file_size(data['platform'], data['version'])
		password = v.get_upgrade_password(mac, filesize)
		dp_info_dic[dp]['password'] = password
		dp_info_dic[dp]['status'] = 'init'


def upgrade_worker(q, v, dp_info_dic, timeout=5):
	while not stopping.is_set():
		try:
			dp = q.get(True, timeout)
			if not v.lock_device(dp):
				print(f'DP {dp}: skipping upgrade process...')
				dp_info_dic[dp]['status'] = 'error'
				continue

			location = v.upgrade_dp(dp, dp_info_dic[dp]['image'], dp_info_dic[dp]['password'])
			if not location:
				dp_info_dic[dp]['status'] = 'error'
				return
			
			dp_info_dic[dp]['location'] = location
			dp_info_dic[dp]['status'] = 'monitoring'
		except queue.Empty:
			continue

		q.task_done()

def bulk_monitoring(dp_info_dic, v):
	while True:
		monitor_flag = False

		for dp in dp_info_dic:
			if dp_info_dic[dp]['status'] == 'error' or dp_info_dic[dp]['status'] == 'ok':
				continue

			monitor_flag = True

			result = v.monitor_upgrade(dp, dp_info_dic[dp]['location'])
			if result['status'] == 'error':
				print(f'DP {dp}: there was an error upgrading DP, "{result["message"]}"')
				dp_info_dic[dp]['status'] = 'error'
				continue

			if result['status'] == 'Processing' and dp_info_dic[dp]['status'] == 'monitoring':
				print(f'DP {dp}: upgrade status "{result["DeviceSoftwareUpdateMode"]}"')
				dp_info_dic[dp]['status'] = 'processing'
				continue

			if result['status'] == 'ok':
				print(f'DP {dp}: upgrade successful')
				dp_info_dic[dp]['status'] = 'ok'

		if not monitor_flag: 
			break

		time.sleep(5)

def print_summary(dp_info_dic):
	for dp,data in dp_info_dic.items():
		if data['status']=='ok':
			print(f'DP {dp}: upgrade process completed successfully')
		
		if data['status']=='error':
			print(f'DP {dp}: upgrade failed')

def main():
	dp_info_dic = {}
	
	if len(sys.argv) != 6:
		print("Usage: python3 DP_bulk_upgrader.py <Vision IP> <Username> <Password> <Excel File Name> <Concurrency 1-5>")
		exit(0)

	if int(sys.argv[5]) <= 0 or int(sys.argv[5]) >= 6:
		print('Error: supported concurrency is between 1 to 5')
		print("Usage: python3 DP_bulk_upgrader.py <Vision IP> <Username> <Password> <Excel File Name> <Concurrency>")
		

	v = Vision(sys.argv[1], sys.argv[2], sys.argv[3])
	e = ExcelParser(sys.argv[4])
	
	print('Fetching all upgrade data...')
	build_dp_database(e, v, dp_info_dic)

	q = queue.Queue()

	print(f'Starting bulk upgrade with {sys.argv[5]} workers')
	for _ in range(int(sys.argv[5])):
		threading.Thread(target=upgrade_worker, args=(q, v, dp_info_dic)).start()

	for dp in dp_info_dic:
		q.put(dp)

	q.join()
	stopping.set()

	bulk_monitoring(dp_info_dic, v)
	print('Bulk upgrade finished...')

	print('------Upgrade Summary------')
	print_summary(dp_info_dic)

main()