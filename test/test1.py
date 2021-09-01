import asyncio

class Testclass:
	def __init__(self, testparam) -> None:
		self.testfield = testparam

	async def testmember(arg):
		print("Member functioning")
		print(arg)

async def testfunc():
	print("Function functioning")

testobj = Testclass(12)
asyncio.run(testfunc())
asyncio.run(testfunc())
asyncio.run(testobj.testmember())
# asyncio.create_task(testfunc())
#asyncio.get_event_loop.run_forever()