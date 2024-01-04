import sys
import threading
import types
import weakref
from types import NoneType
from typing import (
    Protocol,
    Any,
    Generic,
    TypeVar,
    overload,
    get_type_hints,
    Container,
    Iterable,
    Callable,
    Sequence,
    IO,
)

try:
    import venusian

    venusian_attach = venusian.attach
except ImportError:
    venusian = None

    def venusian_attach(*a, **kw):
        pass


class Factory(Protocol):
    """
    A factory for services. A factory is a callable that takes a container
    and returns a service.
    """

    def __call__(self, container: "Container") -> Any:  # pragma: no cover
        """
        Create a service.

        :param container: The container to pass to the service for
        dependencies
        :return: The newly created service
        """


class _AutoMeta(type):
    def __repr__(self):
        return "<auto>"


class auto(metaclass=_AutoMeta):
    """
    A special value that can be used as an interface to autowire a service.
    The interface is resolved from the type hint of the attribute the `autowired`
    descriptor is assigned to.
    """


this = object()

T = TypeVar("T")


class autowired(Generic[T]):
    """
    A descriptor that resolves a service from a container. The descriptor
    resolves the service when it is accessed, and caches the service for the
    lifetime of the object it is accessed from.

    The descriptor can be used in a class definition to resolve a service

            class Foo:
                bar: Bar = autowired(auto)
    """

    interface: type[T] | type[object] | None = None
    names: list[str]

    def __init__(
        self,
        interface: type[T] | type[object] = object,
        *,
        name: str = "",
        context: Any = None,
    ):
        if interface is not auto:
            self.interface = interface

        self.iname = name
        self.context = context
        self.names: list[str] = []

    @overload
    def __get__(self, inst: None, objtype: None) -> "autowired[T]":
        ...

    @overload
    def __get__(self: "autowired[auto]", inst: Any, objtype: None) -> Any:
        ...

    @overload
    def __get__(self: "autowired[object]", inst: Any, objtype: None) -> Any:
        ...

    @overload
    def __get__(self, inst: Any, objtype: Any = None) -> T:
        ...

    def __get__(
        self, inst: object | None, objtype: type[object] | None = None
    ) -> T | "autowired[T]":
        if inst is None:
            return self

        if self.interface is None:
            raise TypeError(
                "Cannot use autowired with `auto` interface without "
                "explicitly specifying the interface in a type hint."
            )

        val = inst.container.get(
            interface=self.interface,
            name=self.iname,
            context=self.context,
        )

        for name in self.names:
            setattr(inst, name, val)

        return val

    def __set_name__(self, owner, name):
        self.names.append(name)

        if self.interface is None:
            hints = get_type_hints(owner)
            self.interface = hints.get(name, None)


class _ContextDiscriminator(dict[type | None, Factory]):
    pass


class _AdapterRegistry:
    lock: threading.RLock
    by_type_and_name: dict[tuple[type, str], _ContextDiscriminator]

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
        interface: type = object,
        name: str = "",
        context_type: type | None = None,
        factory: Factory,
    ):
        with self.lock:
            if (interface, name) not in self.by_type_and_name:
                self.by_type_and_name[interface, name] = _ContextDiscriminator()

            self.by_type_and_name[interface, name][context_type] = factory


class FactoryRegistry:
    def __init__(self, scope: str, supports_contexts: bool = False):
        self.scope = scope
        self.registry = _AdapterRegistry()
        self.supports_contexts = supports_contexts

    def register(
        self,
        *,
        interface: type = object,
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

    def dump(self, indent: int = 0, stream: IO[str] | None = None) -> None:
        """
        Dump the registry to the given stream. If no stream is given,
        sys.stderr is used.

        :param indent: The indentation level to use
        :param stream: The stream to dump to
        """

        if stream is None:
            stream = sys.stderr

        for (
            interface,
            name,
        ), context_discriminator in self.registry.by_type_and_name.items():
            print(
                " " * indent + f"Factory for {interface.__qualname__} named "
                f"{name!r}:",
                file=stream,
            )
            for context_type, factory in context_discriminator.items():
                print(
                    " " * (indent + 4) + f"Context {context_type}: {factory}",
                    file=stream,
                )


class FactoryRegistrySet:
    """
    A set of registries for different scopes. A registry set can create new
    registries for scopes, and scan packages for services.
    """

    _registries: dict[str, FactoryRegistry]

    def __init__(self):
        self._registries = {}

    def create_registry(
        self, scope: str, supports_contexts: bool = False
    ) -> FactoryRegistry:
        """
        Create a new registry for a scope. If a registry for the scope already
        exists, a KeyError is raised.

        :param scope: The scope to create the registry for
        :param supports_contexts: Whether the registry supports contexts
        :return: The created registry
        """
        if scope in self._registries:
            raise KeyError(f"Registry for scope {scope!r} already exists")

        registry = FactoryRegistry(scope, supports_contexts)
        self._registries[scope] = registry
        return registry

    def get_registry(self, scope: str) -> FactoryRegistry:
        """
        Get a registry for a scope. If a registry for the scope does not exist,
        a KeyError is raised.

        :param scope: The scope to get the registry for
        :return: The registry
        """
        try:
            return self._registries[scope]
        except KeyError:
            raise KeyError(f"No registry for scope {scope!r}")

    def scan_services(
        self,
        package: types.ModuleType,
        *,
        categories: Iterable[str] = ("anemic.service",),
        onerror: Callable[[str], None] | None = None,
        ignore: Sequence[str | Callable[[str], bool]] | None = None,
    ):
        """
        Scan a package or module for services. The package is scanned using
        venusian.
        If venusian is not installed, a RuntimeError is raised.

        :param package: The package or module to scan
        :param categories: The categories to scan for. Defaults to only
        `"anemic.service"`
        :param onerror: A callback to call when an error occurs. Defaults to
        None. See venusian.Scanner.scan for more information
        :param ignore: A list of names or callables to ignore. Defaults to
        None. See venusian.Scanner.scan for more information
        """
        if venusian is None:
            raise RuntimeError(
                "Venusian is not installed but it is required for scanning"
            )

        scanner = venusian.Scanner(registry_set=self)

        scanner.scan(
            package,
            categories=tuple(categories),
            onerror=onerror,
            ignore=ignore,
        )

    def dump(self, indent: int = 0, stream: IO[str] | None = None) -> None:
        """
        Dump the registries in the registry set to given stream.
        If no stream is given, sys.stderr is used.

        :param indent: The indentation level to use
        :param stream: The stream to dump to
        """

        if stream is None:
            stream = sys.stderr

        for scope, registry in self._registries.items():
            print(" " * indent + f"Registry for scope {scope!r}:", file=stream)
            registry.dump(indent + 4, stream=stream)


class _ServiceCache:
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


class _ContextServiceCache:
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
                self.cache[id_] = _ServiceCache()

            return self.cache[id_]


class Container:
    """
    A container for services. A container resolves services from a registry,
    and caches them for the lifetime of the container. A container can have a
    parent container, which is used to resolve services that are not registered
    in the container itself.
    """

    context_caches: _ContextServiceCache

    def __init__(
        self,
        factory_registry: FactoryRegistry,
        parent: "Container | None" = None,
    ):
        """
        Create a new container.

        :param factory_registry: The registry to resolve services from
        :param parent: The parent container to resolve services from if they
        are not registered in this container
        """
        self.factory_registry = factory_registry
        self.context_caches = _ContextServiceCache()
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
        """
        Resolve a service from the registry. If the service is not registered
        in the registry, the parent container is used to resolve the service.
        If the service is not registered in the parent container, a LookupError
        is raised.

        :param interface: The interface to resolve the service for
        :param name: The name to resolve the service for
        :param context: The context to resolve the service for
        :return: The resolved service
        """
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

            name_part = ""
            if name:
                name_part = f" named {name!r}"

            context_part = ""
            if context:
                context_part = f" (in context {context!r})"

            raise LookupError(
                f"Could not resolve a factory for {interface.__name__}"
                f"{name_part}"
                f"{context_part}"
            )


def service(
    interface_override: type | None = None,
    *,
    name: str = "",
    context_type: type | None = None,
    scope: str,
):
    """
    A decorator that registers a service factory in a registry.

    :param interface_override: The interface to register the service under.
    If not specified, the interface is the decorated class
    :param name: The name to register the service under. If not specified,
    the name is empty (corresponding to unnamed services)
    :param context_type: The context type to register the service under.
    If not specified, the context type is not set. If specified, the scoped
    registry must support contexts.
    :param scope: The scope to register the service under. The scope must be
    supported by the registry.
    """
    registration_name = name

    def service_decorator(wrapped):
        def callback(scanner, name, ob):
            interface = interface_override
            if interface is None:
                interface = ob

            registry_set: FactoryRegistrySet = scanner.registry_set
            registry = registry_set.get_registry(scope)

            print(
                f"Registering {interface.__name__} named "
                f"{registration_name!r} in "
                f"context {context_type}"
                f" in scope {scope}",
            )
            registry.register(
                interface=interface,
                name=registration_name,
                context_type=context_type,
                factory=ob,
            )

        venusian_attach(wrapped, callback, category="anemic.service")
        return wrapped

    return service_decorator
