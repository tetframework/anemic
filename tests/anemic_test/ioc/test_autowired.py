import pytest

from anemic.ioc.autowired import autowired
from anemic.ioc.container import FactoryRegistry, IOCContainer


class ServiceA:
    times_inited = 0

    def __init__(self, container):
        ServiceA.times_inited += 1
        self.container = container

    def foo(self):
        return "foo"


class ServiceB:
    a = autowired(ServiceA)

    def __init__(self, container):
        self.container = container

    def foobar(self):
        return self.a.foo() + "bar"


@pytest.fixture(autouse=True)
def setup():
    ServiceA.times_inited = 0


@pytest.fixture
def registry():
    ret = FactoryRegistry("application")
    ret.register(
        interface=ServiceA,
        factory=ServiceA,
    )
    ret.register(
        interface=ServiceB,
        factory=ServiceB,
    )
    return ret


@pytest.fixture
def container(registry):
    return IOCContainer(registry)


def test_autowired_attribute_access(container: IOCContainer):
    assert ServiceA.times_inited == 0  # sanity
    b = container.get(interface=ServiceB)
    assert ServiceA.times_inited == 0  # ServiceA not initialized yet
    a = b.a
    assert ServiceA.times_inited == 1  # ServiceA initialized after b.a accessed
    assert isinstance(a, ServiceA)
    assert a is b.a  # same instance
    assert ServiceA.times_inited == 1  # ServiceA not initialized again


def test_autowired_method_call(container: IOCContainer):
    b = container.get(interface=ServiceB)
    assert b.foobar() == "foobar"
