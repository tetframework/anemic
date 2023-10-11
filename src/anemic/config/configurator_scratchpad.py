import copy
import importlib
import sqlalchemy
import sqlalchemy.engine
import sqlalchemy.orm.session
import anemic.blocks.sqlalchemy

from anemic.ioc.container import FactoryRegistry, IOCContainer

anemic.blocks.sqlalchemy.create_registry(
    url='postgresql://'
)

anemic.blocks.sqlalchemy.include(
    url='postgresql://',
    global_registry=...,
    request_registry=...,
)

config = anemic.Configurator()
config.include(
    'anemic.blocks.sqlalchemy',
    url='postgresql://',
)


def anemic_include(
    config,
    *,
    url: str,
):
    global_registry = config.get_registry('global')
    global_registry.register(
        interface=sqlalchemy.engine.Engine,
        factory=lambda c: sqlalchemy.create_engine(url),
    )
    global_registry.register(
        interface=sqlalchemy.orm.sessionmaker,
        factory=lambda c: sqlalchemy.orm.sessionmaker(
            bind=c.get(interface=sqlalchemy.engine.Engine),
        ),
    )
    request_registry = config.get_registry('request')
    request_registry.register(
        interface=sqlalchemy.orm.Session,
        factory=lambda c: c.get(interface=sqlalchemy.orm.sessionmaker)(),
    )


def test_mytest():
    testconfig = Configurator()
    testconfig.override_include(
        'anemic.blocks.sqlalchemy',
        module=mysqlamodule,
        url='postgresql://',
    )
    testconfig.foo(config)


config.create_container('global')


# V1

class Configurator:
    def __init__(
        self,
        includes: dict = None,
        registries: dict = None
    ):
        self._includes = includes.copy() if includes else {}
        self._registries = copy.deepcopy(registries) if registries else {}

    def copy(self):
        return Configurator(
            includes=self._includes,
            registries=self._registries,
        )

    def include(self, module_name, *args, **kwargs):
        if module_name in self._includes:
            return  # including is impotent
        module = importlib.import_module(module_name)
        if not hasattr(module, 'anemic_include'):
            raise ValueError(f"Module {module_name} does not support anemic_include")
        self._includes[module_name] = (module, args, kwargs)

    def override_include(self, module_name, module, *args, **kwargs):
        if module_name not in self._includes:
            raise ValueError(f"Module {module_name} not included and thus cannot be overridden")
        if not hasattr(module, 'anemic_include'):
            raise ValueError(f"Module {module_name} does not support anemic_include")
        self._includes[module_name] = (module, args, kwargs)

    def get_registry(self, scope='global'):
        if scope not in self._registries:
            self._registries[scope] = FactoryRegistry(scope)
        return self._registries[scope]

    def process_includes(self):
        while self._includes:
            includes = self._includes.copy()
            self._includes.clear()
            for module_name, (module, args, kwargs) in includes.items():
                module.anemic_include(self, *args, **kwargs)


# V2


class LazyConfigurator:
    def __init__(self, includes: dict = None):
        self._includes = includes.copy() if includes else {}

    def copy(self):
        return LazyConfigurator(
            includes=self._includes,
        )

    def include(self, module_name, *args, **kwargs):
        if module_name in self._includes:
            return  # including is impotent. Different args should be handled though.
        module = importlib.import_module(module_name)
        if not hasattr(module, 'anemic_include'):
            raise ValueError(f"Module {module_name} does not support anemic_include")
        self._includes[module_name] = (module, args, kwargs)

    def override_include(self, module_name, module, *args, **kwargs):
        if module_name not in self._includes:
            raise ValueError(f"Module {module_name} not included and thus cannot be overridden")
        if not hasattr(module, 'anemic_include'):
            raise ValueError(f"Module {module_name} does not support anemic_include")
        self._includes[module_name] = (module, args, kwargs)

    def process_includes(self) -> 'DiligentConfigurator':
        configurator = DiligentConfigurator()
        for module_name, (module, args, kwargs) in self._includes.items():
            module.anemic_include(configurator, *args, **kwargs)
        return configurator


class DiligentConfigurator:
    def __init__(self):
        self._registries = {}

    def include(self, module_name, *args, **kwargs):
        module = importlib.import_module(module_name)
        module.anemic_include(self, *args, **kwargs)

    def get_registry(self, scope='global'):
        if scope not in self._registries:
            self._registries[scope] = FactoryRegistry(scope)
        return self._registries[scope]

    def register(
        self,
        *,
        scope='global',
        interface=object,
        name='',
        factory=None,
    ):
        self.get_registry(scope).register(
            interface=interface,
            name=name,
            factory=factory,
        )

    def create_container(self, scope='global', parent=None):
        return IOCContainer(self.get_registry(scope), parent=parent)
