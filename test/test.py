import asyncio

task = "hi"


async def hello():
    global task
    for i in range(4):    
        print('Hello')
        await asyncio.sleep(1)
    task.cancel()
    # await asyncio.sleep(1) this would give execution back to the event loop, so that the code below is never called
    # task = asyncio.create_task(bye())


async def bye():
    while True:
        print('Bye')
        await asyncio.sleep(1)


async def main():
    global task
    task = asyncio.create_task(hello())
    await asyncio.sleep(5)
    task.cancel()

asyncio.run(main())
asyncio.get_event_loop().run_forever()

