# generate unitttests for anemic.ioc.container
from itertools import count
from unittest.mock import sentinel

from pytest import raises
from anemic.ioc.container import IOCContainer, FactoryRegistry


def test_ioc_container():
    application_registry = FactoryRegistry("application")
    request_registry = FactoryRegistry("request")

    foo = sentinel.foo
    application_registry.register_singleton(name="foo", singleton=foo)

    bar_called = 0

    def bar_factory(container: IOCContainer):
        nonlocal bar_called
        bar_called += 1
        return bar_called

    application_registry.register(name="bar", factory=bar_factory)
    application_registry.register(name="barf", factory=bar_factory)
    request_registry.register(name="barfoo", factory=bar_factory)

    app_container = IOCContainer(application_registry)
    request_container = IOCContainer(request_registry, app_container)
    request_container2 = IOCContainer(request_registry, app_container)
    assert request_container.get(name="foo") is foo
    assert request_container.get(name="bar") == 1
    assert request_container.get(name="bar") == 1
    assert app_container.get(name="bar") == 1

    assert request_container2.get(name="bar") == 1

    # same factory, but different name, yields newly
    # constructed object
    assert app_container.get(name="barf") == 2
    assert request_container2.get(name="barf") == 2

    # distinct containers do not share state
    assert request_container2.get(name="barfoo") == 3
    assert request_container.get(name="barfoo") == 4

    # the following raises LookupError, as there is no factory registered for
    # the name 'barfoo' in the application registry.
    with raises(LookupError):
        app_container.get(name="barfoo")


def test_interfaces():
    application_registry = FactoryRegistry("application")
    request_registry = FactoryRegistry("request")

    app_container = IOCContainer(application_registry)
    request_container = IOCContainer(request_registry, app_container)
    request_container2 = IOCContainer(request_registry, app_container)

    ct = count(1)

    class IFoo:
        def __init__(self, container):
            self.id = next(ct)

    class IBar:
        def __init__(self, container):
            self.id = next(ct)

    application_registry.register_singleton(
        interface=IFoo, name="foo", singleton=IFoo(app_container)
    )
    application_registry.register_singleton(
        interface=IFoo, singleton=IFoo(app_container)
    )
    request_registry.register(interface=IFoo, name="foo2", factory=IFoo)

    assert request_container.get(interface=IFoo, name="foo").id == 1
    assert request_container.get(interface=IFoo).id == 2

    # distinct containers get distinct results
    assert request_container.get(interface=IFoo, name="foo2").id == 3
    assert request_container2.get(interface=IFoo, name="foo2").id == 4

    # test same name but different interface
    with raises(LookupError):
        # we did not register a factory for IBar
        request_container2.get(interface=IBar, name="foo2")

    request_registry.register(interface=IBar, name="foo2", factory=IBar)
    assert request_container2.get(interface=IBar, name="foo2").id == 5
    assert request_container.get(interface=IBar, name="foo2").id == 6

    with raises(LookupError):
        app_container.get(interface=IBar, name="foo2")


def test_contexts():
    application_registry = FactoryRegistry("application")
    request_registry = FactoryRegistry("request", supports_contexts=True)

    app_container = IOCContainer(application_registry)
    request_container = IOCContainer(request_registry, app_container)
    request_container2 = IOCContainer(request_registry, app_container)

    ct = count(1)

    class FooContext:
        def __init__(self, ID):
            self.id = ID

    class BarContext(FooContext):
        pass

    class Service:
        def __init__(self, id):
            self.id = next(ct)

    application_registry.register(
        name="foo",
        factory=Service,
    )

    request_registry.register(
        context_type=BarContext,
        name="foo",
        factory=Service,
    )

    # get the FooContext service
    assert app_container.get(context=FooContext(1), name="foo").id == 1
    assert app_container.get(context=BarContext(1), name="foo").id == 1

    # get the indiscrimanted service from aplication registry
    assert request_container.get(context=FooContext(1), name="foo").id == 1

    # get the BarContext specific instance
    assert request_container.get(context=BarContext(1), name="foo").id == 2

    # get another BarContext specific instance from the same container
    assert request_container.get(context=BarContext(1), name="foo").id == 3


def test_container_raises_when_illegal_context():
    application_registry = FactoryRegistry("application")
    with raises(TypeError):
        application_registry.register(
            name="foo",
            factory=lambda: None,
            context_type=int,
        )

    with raises(TypeError):
        application_registry.register_singleton(
            name="foo",
            singleton="foo",
            context_type=int,
        )

    request_registry = FactoryRegistry("request", supports_contexts=True)
    request_container = IOCContainer(
        request_registry,
        IOCContainer(application_registry),
    )

    request_registry.register_singleton(
        name="foo",
        singleton="foo",
        context_type=int,
    )

    with raises(TypeError):
        # raise when context is not weakrefable
        request_container.get(name="foo", context=1)


def test_resolve_with_context_type_throws_on_context_not_supported():
    application_registry = FactoryRegistry("application")
    application_registry.register(
        name="foo",
        factory=lambda: None,
    )
    with raises(TypeError):
        application_registry.resolve(name="foo", context_type=int)

    # does not raise when context_type is None
    application_registry.resolve(name="foo", context_type=None)
