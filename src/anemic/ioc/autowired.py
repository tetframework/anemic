from typing import Any, TypeVar, cast

from ..decorators import reify_attr

__all__ = [
    "autowired",
]

T = TypeVar("T")


class SentinelType(Any):
    pass


def autowired(
    interface: type[T] = SentinelType,
    *,
    name: str = "",
    context: Any = None,
) -> T:
    # Default for IOCContainer.get is object
    if interface is SentinelType:
        interface = cast(type[T], object)

    @reify_attr[T]
    def getter(self) -> T:
        return self.container.get(
            interface=interface,
            name=name,
            context=context,
        )

    # TODO: cast to T from reify_attr[T], because PyCharm
    # doesn't understand types of custom descriptors
    return cast(T, getter)
