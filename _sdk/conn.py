import asyncio
import mavsdk

async def main():
	mav = mavsdk.System()
	await mav.connect(system_address='serial:///dev/ttyAMA0')
	v = await mav.info.get_version()
	print(v)

asyncio.run(main())
