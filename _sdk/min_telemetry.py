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
	async for status in mav.telemetry.battery():
		logging.info(status)
	logging.info('bye')

asyncio.run(main())
