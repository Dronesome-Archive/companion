import asyncio
from random import randint

async def init():
	print("starting")
	asyncio.create_task(indefinite_task(1))
	await asyncio.create_task(indefinite_task(2))
	print("startup finished")

async def indefinite_task(i):
	while True:
		await asyncio.sleep(randint(0, 10))
		print(f"task {i} did something")

# asyncio.create_task(init()) # this would error (no running event loop), so we use asyncio.run intead
asyncio.run(init()) # on its own, this exits right away
# asyncio.get_event_loop().run_forever() # error (There is no current event loop in thread 'MainThread')