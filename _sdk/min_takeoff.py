import asyncio
import mavsdk
import logging

async def main():
	logging.getLogger().setLevel(logging.DEBUG)
	mav = mavsdk.System()
	await mav.connect(system_address='serial:///dev/ttyAMA0')
	async for state in mav.core.connection_state():
		logging.info(state)
		if state.is_connected:
			break
	await mav.param.set_param_int('COM_RC_IN_MODE', 2)
	logging.info('changed param')
	logging.info("waiting for global position estimate...")
	async for health in mav.telemetry.health():
		logging.info(health)
		if health.is_global_position_ok:
			logging.info("is_global_position_ok")
			break
	logging.info("arming")
	await mav.action.arm()
	print("taking off")
	await mav.action.takeoff()
	await asyncio.sleep(5)
	print("landing")
	await mav.action.land()
	logging.info('bye')

asyncio.run(main())
