from abc import ABCMeta

from zope.interface import Interface as _ZInterface


class _InterfaceBase(ABCMeta):
    def __new__(mcs, name, bases, attrs, *, __zope_interface__=None):
        if __zope_interface__ is not None:
            rv = super().__new__(mcs, name, bases, attrs)
            rv.__zope_interface__ = __zope_interface__
            return rv

        return InterfaceImplementor(name, bases, attrs)

    def __init__(cls, name, bases, attrs, *, __zope_interface__=None):
        print(type(cls))

        print(cls.__name__, cls.__qualname__, cls.__module__)

        super().__init__(name, bases, attrs)

    @property
    def zope_interface(cls):
        return cls.__zope_interface__


class InterfaceImplementor(_InterfaceBase):
    def __new__(mcs, name, bases, attrs, *, is_interface=False):
        attrs["__interface__"] = None
        return ABCMeta.__new__(mcs, name, bases, attrs)

    @property
    def zope_interface(cls):
        raise AttributeError(
            "{} is not a SimpleInterface, and "
            "therefore has no Zope Interface".format(cls)
        )


def SimpleInterface(name, bases, attrs):
    modname = attrs.get("__module__")
    if modname:
        modname += ".autogenerated_interfaces"
    namespace = {"__module__": modname, "__qualname__": attrs.get("qualname")}
    zinterface = _ZInterface.__class__(name, (_ZInterface,), namespace)
    # TODO: actually do the interface description here

    created = _InterfaceBase(name, bases, attrs, __zope_interface__=zinterface)
    return created
