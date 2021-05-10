import requests
import asyncio
import json
from mavsdk import (System, mission, telemetry)
import mission
import logging


APIENDPOINT = 'https://dronesem.studio'
APICERT = 'root-ca.crt'
DRONECERT = './drone.crt'
DRONEKEY = './drone.key'

drone = System()
currentMission = None

# set up logging
logging.basicConfig(
	filename='./drone.log',
	level=logging.DEBUG,
	format='%(levelname)s %(asctime)s - %(message)s'
)
logger = logging.getLogger()


# update internal mission according to server and forward to pixhawk
def updateMission():

	# query and decode new mission
	newMission = None
	try:
		req = requests.get(APIENDPOINT + '/drone/mission', cert=(DRONECERT, DRONEKEY), verify=APICERT)
		battery = await drone.telemetry.battery()
		newMission = Mission(req.json(), battery)
	except Exception as e:
		logger.error('updateMission failed! Err:' + print(e) + 'Req: ' + req.text)
		return
	if newMission.id == mission.id:
		logger.warn('newMission was same as old mission')
		return
	
	# start new mission
	# TODO: figure out asyncio
	missionPlan = MissionPlan(currentMission.getItems())
	await drone.mission.set_return_to_launch_after_mission(True)
	await drone.mission.upload_mission(missionPlan)
	await drone.action.arm()
	await drone.mission.start_mission()