import threading
import weakref
from types import NoneType
from typing import Protocol, Any


class Factory(Protocol):
    def __call__(self, container: "IOCContainer") -> Any:  # pragma: no cover
        ...


class ContextDiscriminator(dict[type | None, Factory]):
    pass


class AdapterRegistry:
    lock: threading.RLock
    by_type_and_name: dict[tuple[type, str], ContextDiscriminator]

    def __init__(self):
        self.lock = threading.RLock()
        self.by_type_and_name = {}

    def get(
        self,
        *,
        interface: type = object,
        name: str = "",
        context_type: type | None = None,
    ):
        return self.by_type_and_name[interface, name][context_type]

    def set(
        self,
        *,
        interface=object,
        name: str = "",
        context_type: type | None = None,
        factory: Factory,
    ):
        with self.lock:
            if (interface, name) not in self.by_type_and_name:
                self.by_type_and_name[interface, name] = ContextDiscriminator()

            self.by_type_and_name[interface, name][context_type] = factory


class FactoryRegistry:
    def __init__(self, scope: str, supports_contexts: bool = False):
        self.scope = scope
        self.registry = AdapterRegistry()
        self.supports_contexts = supports_contexts

    def register(
        self,
        *,
        interface=object,
        name: str = "",
        factory: Factory,
        context_type: type | None = None,
    ):
        if not self.supports_contexts and context_type is not None:
            raise TypeError(f"FactoryRegistry({self.scope}) does not support contexts")

        self.registry.set(
            interface=interface,
            name=name,
            context_type=context_type,
            factory=factory,
        )

    def register_singleton(
        self,
        *,
        interface=object,
        name: str = "",
        context_type: type | None = None,
        singleton: Any,
    ):
        if not self.supports_contexts and context_type is not None:
            raise TypeError(f"FactoryRegistry({self.scope}) does not support contexts")

        self.registry.set(
            interface=interface,
            name=name,
            context_type=context_type,
            factory=lambda _: singleton,
        )

    def resolve(
        self,
        *,
        interface: type = object,
        name: str = "",
        context_type: type | None = None,
    ):
        if not self.supports_contexts and context_type is not None:
            raise TypeError(f"FactoryRegistry({self.scope}) does not support contexts")

        return self.registry.get(
            interface=interface,
            name=name,
            context_type=context_type,
        )


class ServiceCache:
    lock: threading.RLock

    def __init__(self):
        self.cache = {}
        self.lock = threading.RLock()

    def get(
        self,
        *,
        interface: type = object,
        name: str = "",
    ):
        with self.lock:
            return self.cache[interface, name]

    def set(
        self,
        *,
        interface: type = object,
        name: str = "",
        service: Any,
    ):
        with self.lock:
            self.cache[interface, name] = service


class ContextServiceCache:
    lock: threading.RLock

    def __init__(self):
        self.cache = {}
        self.lock = threading.RLock()

    def get(
        self,
        *,
        context: Any,
    ):
        id_ = id(context)
        with self.lock:
            if context is not None:
                try:
                    weakref.finalize(context, self.cache.pop, id_, None)
                except TypeError:
                    raise TypeError(f"Context {context} is not weakly referenceable")

            if id_ not in self.cache:
                self.cache[id_] = ServiceCache()

            return self.cache[id_]


class IOCContainer:
    context_caches: ContextServiceCache

    def __init__(
        self,
        factory_registry: FactoryRegistry,
        parent: "IOCContainer | None" = None,
    ):
        self.factory_registry = factory_registry
        self.context_caches = ContextServiceCache()
        self.scope = factory_registry.scope
        self.parent = parent

    def _get_mro(self, context_object):
        if context_object is None:
            return [None]

        mro = list(type(context_object).__mro__)
        return mro

    def get(
        self,
        *,
        interface: type = object,
        name: str = "",
        context: Any = None,
    ):
        if not self.factory_registry.supports_contexts:
            context = None

        context_cache = self.context_caches.get(context=context)
        try:
            return context_cache.get(
                interface=interface,
                name=name,
            )
        except KeyError:
            pass

        for context_type in self._get_mro(context):
            try:
                factory = self.factory_registry.resolve(
                    interface=interface,
                    name=name,
                    context_type=context_type,
                )
                service = factory(self)
                context_cache.set(
                    interface=interface,
                    name=name,
                    service=service,
                )
                return service
            except KeyError:
                pass

        if self.parent is not None:
            return self.parent.get(
                interface=interface,
                name=name,
                context=context,
            )
        else:
            reported: Any = interface
            if interface is object:
                reported = Any

            raise LookupError(
                f"Could not resolve {interface.__name__} named {name!r} in context {context}"
            )
