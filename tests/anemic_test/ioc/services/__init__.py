from anemic.ioc import service, Container, autowired, auto


@service(scope="application")
class Bar:
    counter = 0

    def __init__(self, container: Container):
        self.container = container

    def delegate(self) -> int:
        self.counter += 1
        return self.counter


@service(scope="request")
class Foo:
    bar: Bar = autowired(auto)
    named_bar: Bar = autowired(auto, name="named_bar")

    def __init__(self, container: Container):
        self.container = container

    def delegate(self) -> str:
        return f"delegated: {self.bar.delegate()}"

    def delegate_to_named(self) -> str:
        return f"delegated to named: {self.named_bar.delegate()}"
