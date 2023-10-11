from __future__ import annotations

import warnings
from functools import update_wrapper
from typing import TypeVar, Generic
from typing import overload


def deprecated(func):
    """This is a decorator which can be used to mark functions
    as deprecated. It will result in a warning being emitted
    when the function is used."""

    def new_func(*args, **kwargs):
        warnings.warn(
            "Call to deprecated function {}.".format(
                func.__qualname__,
            ),
            category=warnings.DeprecationWarning,
            stacklevel=2,
        )

        return func(*args, **kwargs)

    new_func.__name__ = func.__name__
    new_func.__doc__ = func.__doc__
    new_func.__dict__.update(func.__dict__)
    return new_func


T = TypeVar("T")


class reify_attr(Generic[T]):
    """
    reify_attr is like pyramid reify, but instead of getting the name of the
    attribute from the decorated method, it uses the name of actual attribute.
    """

    def __init__(self, wrapped):
        self.wrapped = wrapped
        update_wrapper(self, wrapped)
        self.names = None

    @overload
    def __get__(self, inst: None, objtype: None) -> reify_attr[T]:
        ...

    @overload
    def __get__(self, inst: object, objtype: type[object]) -> T:
        ...

    def __get__(
        self, inst: object | None, objtype: type[object] | None = None
    ) -> reify_attr[T] | T:
        if inst is None:
            return self

        val = self.wrapped(inst)
        for name in self.names:
            setattr(inst, name, val)

        return val

    def __set_name__(self, owner, name):
        if self.names is None:
            self.names = [name]
        else:
            self.names.append(name)
