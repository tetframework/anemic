import re
from typing import Type, TypeVar

import venusian
from pyramid.config import Configurator
from anemic.decorators import reify_attr
from zope.interface import Interface
from zope.interface.interface import InterfaceClass

_to_underscores = re.compile('((?<=[a-z0-9])[A-Z]|(?!^)[A-Z](?=[a-z]))')


def _underscore(name):
    return _to_underscores.sub(r'_\1', name).lower()


_is_iface_name = re.compile('^I[A-Z].*')


class ServiceRegistry(object):
    def __init__(self):
        self.__services__ = []

    def _register_service(self, instance, interface):
        self.__services__.append((instance, interface))
        name = interface.__name__
        if _is_iface_name.match(name):
            name = name[1:]

        setattr(self, _underscore(name), instance)


def get_service_registry(registry):
    if not hasattr(registry, 'services'):
        registry.services = ServiceRegistry()

    return registry.services


def register_anemic_service(config: Configurator,
                         service_factory,
                         *,
                         scope='global',
                         interface=Interface,
                         name='',
                         context_iface=Interface):
    registry = config.registry
    if scope == 'global':
        # register only once
        if registry.queryUtility(interface, name=name) is None:
            ob_instance = service_factory(registry=registry)
            get_service_registry(registry)._register_service(ob_instance,
                                                             interface)

            # only classes can be registered.
            if isinstance(interface, InterfaceClass):
                registry.registerUtility(ob_instance,
                                         interface,
                                         name=name)

            config.register_service(
                service=ob_instance,
                iface=interface,
                context=context_iface,
                name=name)

    else:
        # noinspection PyUnusedLocal
        def wrapped_factory(context, request):
            return service_factory(request=request)

        config.register_service_factory(
            wrapped_factory,
            interface,
            context_iface,
            name=name)


def service(interface=Interface,
            name='',
            context_iface=Interface,
            scope='global'):
    if scope not in {'global', 'request'}:
        raise ValueError(
            "Invalid scope {}, must be either 'global' or 'request'"
                .format(scope))

    service_name = name

    def service_decorator(wrapped):
        def callback(scanner, name, ob):
            config = scanner.config
            config.register_anemic_service(
                ob,
                name=service_name,
                interface=interface,
                context_iface=context_iface,
                scope=scope
            )

        venusian.attach(wrapped, callback, category='anemic.service')
        return wrapped

    return service_decorator


T = TypeVar('T', bound=object)


def autowired(interface: Type[T] = Interface, name: str = '') -> T:
    @reify_attr
    def getter(self):
        if hasattr(self, 'request'):
            # remove context discrimination. It didn't work anyway.
            return self.request.find_service(interface, None, name)

        return self.registry.getUtility(interface, name)

    return getter


class BaseService(object):
    def __init__(self, **kw):
        try:
            self.registry = kw.pop('registry')
            super(BaseService, self).__init__(**kw)

        except KeyError:
            raise TypeError("Registry to the base business must be provided")


class RequestScopedBaseService(BaseService):
    """
    :type request: pyramid.request.Request
    """

    def __init__(self, **kw):
        try:
            self.request = kw.pop('request')
            kw['registry'] = self.request.registry
            super(RequestScopedBaseService, self).__init__(**kw)

        except KeyError:
            raise TypeError("Request to the base business must be provided")


def scan_services(config, *a, **kw):
    kw['categories'] = ('anemic.service',)
    return config.scan(*a, **kw)


def includeme(config):
    config.include('pyramid_services')
    config.add_directive('scan_services', scan_services)
    config.add_directive('register_anemic_service', register_anemic_service)
    config.registry.services = ServiceRegistry()
