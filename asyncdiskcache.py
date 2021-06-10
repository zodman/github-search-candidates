################################################################################

import asyncio
import functools
import types

from diskcache import Cache


class AsyncMeta(type):
    def __new__(cls, name, bases, attrs):
        base = attrs['__wrapped__']

        def __init__(self, loop=None, executor=None):
            if loop is None:
                loop = asyncio.get_event_loop()
            run = functools.partial(loop.run_in_executor, executor)
            self.__dict__['_async_meta_run'] = run
            self.__dict__['_async_meta_thing'] = None

        assert '__init__' not in attrs
        attrs['__init__'] = __init__

        async def initialize(self, *args, **kwargs):
            """Initialize the thing attribute."""
            func = functools.partial(base, *args, **kwargs)
            thing = await self._async_meta_run(func)
            self.__dict__['_async_meta_thing'] = thing

        assert 'initialize' not in attrs
        attrs['initialize'] = initialize

        def __getattr__(self, name):
            return getattr(self._async_meta_thing, name)

        assert '__getattr__' not in attrs
        attrs['__getattr__'] = __getattr__

        def __setattr__(self, name, value):
            setattr(self._async_meta_thing, name, value)

        assert '__setattr__' not in attrs
        attrs['__setattr__'] = __setattr__

        def __delattr__(self, name):
            delattr(self._async_meta_thing, name)

        assert '__delattr__' not in attrs
        attrs['__delattr__'] = __delattr__

        # TODO: Add support for __aiter__, __anext__, __aenter__, and __aexit__

        def make_method(func):
            """Make an async wrapper method."""
            @functools.wraps(func)
            async def method(self, *args, **kwargs):
                """Async wrapper method."""
                # `AsyncThing` wraps `Thing` so pass `self._async_meta_thing` as the
                # first argument to be bound to `self` in `Thing` method calls.
                call = functools.partial(func, self._async_meta_thing, *args, **kwargs)
                return await self._async_meta_run(call)
            return method

        # Iterate the attributes of the cache and make methods for `AsyncCache`.

        for name in dir(base):
            if name.startswith('_'):
                # Only support the "public" methods.
                continue
            attr = getattr(base, name)
            if not isinstance(attr, types.FunctionType):
                continue
            # TODO: Add support for contextlib.contextmanager types.
            method = make_method(attr)
            attrs[name] = method

        bases = (object,)
        return super().__new__(cls, name, bases, attrs)


class AsyncCache(metaclass=AsyncMeta):
    __wrapped__ = Cache


###############################################################################


async def main():
    cache = AsyncCache()
    await cache.initialize(directory='/tmp/diskcache/async')
    assert cache.directory == '/tmp/diskcache/async'
    await cache.set('key', 'value')
    print(await cache.get('key'))
    async with cache.transact():
        pass

if __name__ == '__main__':
    asyncio.run(main())
