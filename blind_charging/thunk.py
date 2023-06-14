from typing import Any, Callable, Optional


def _method_proxy(inst: Any, name: str, *args, **kwargs) -> Optional[Any]:
    """Proxy the given method to the given object.

    :param inst: Source object
    :param name: Name of method to proxy
    :param *args: Any positional arguments to pass to method
    :param **kwargs: Any keyword arguments to pass to method
    :returns: Result of executing source's method
    """
    obj = object.__getattribute__(inst, "_factory")()
    return object.__getattribute__(obj, name)(*args, **kwargs)


class Thunk(object):
    """A simple lazy-initialized object proxy."""

    __slots__ = ["_factory", "_value", "_called"]

    def __init__(self, f: Callable[[], Any]):
        def _factory():
            if not object.__getattribute__(self, "_called"):
                result = f() if callable(f) else f
                object.__setattr__(self, "_value", result)
                object.__setattr__(self, "_called", True)
            return object.__getattribute__(self, "_value")

        object.__setattr__(self, "_factory", _factory)
        object.__setattr__(self, "_value", None)
        object.__setattr__(self, "_called", False)

    def __getattribute__(self, *args, **kwargs):
        return _method_proxy(self, "__getattribute__", *args, **kwargs)

    def __setattr__(self, *args, **kwargs):
        return _method_proxy(self, "__setattr__", *args, **kwargs)

    def __delattr__(self, *args, **kwargs):
        return _method_proxy(self, "__delattr__", *args, **kwargs)

    def __getitem__(self, *args, **kwargs):
        return _method_proxy(self, "__getitem__", *args, **kwargs)

    def __setitem__(self, *args, **kwargs):
        return _method_proxy(self, "__setitem__", *args, **kwargs)

    def __delitem__(self, *args, **kwargs):
        return _method_proxy(self, "__delitem__", *args, **kwargs)

    def __call__(self, *args, **kwargs):
        return _method_proxy(self, "__call__", *args, **kwargs)

    def __iter__(self, *args, **kwargs):
        return _method_proxy(self, "__iter__", *args, **kwargs)

    def __reversed__(self, *args, **kwargs):
        return _method_proxy(self, "__reversed__", *args, **kwargs)

    def __contains__(self, *args, **kwargs):
        return _method_proxy(self, "__contains__", *args, **kwargs)

    def __missing__(self, *args, **kwargs):
        return _method_proxy(self, "__missing__", *args, **kwargs)

    def __len__(self, *args, **kwargs):
        return _method_proxy(self, "__len__", *args, **kwargs)

    def __str__(self, *args, **kwargs):
        return _method_proxy(self, "__str__", *args, **kwargs)

    def __repr__(self, *args, **kwargs):
        return _method_proxy(self, "__repr__", *args, **kwargs)

    def __unicode__(self, *args, **kwargs):
        return _method_proxy(self, "__unicode__", *args, **kwargs)

    def __format__(self, *args, **kwargs):
        return _method_proxy(self, "__format__", *args, **kwargs)

    def __hash__(self, *args, **kwargs):
        return _method_proxy(self, "__hash__", *args, **kwargs)

    def __nonzero__(self, *args, **kwargs):
        return _method_proxy(self, "__nonzero__", *args, **kwargs)

    def __dir__(self, *args, **kwargs):
        return _method_proxy(self, "__dir__", *args, **kwargs)

    def __sizeof__(self, *args, **kwargs):
        return _method_proxy(self, "__sizeof__", *args, **kwargs)

    def __int__(self, *args, **kwargs):
        return _method_proxy(self, "__int__", *args, **kwargs)

    def __long__(self, *args, **kwargs):
        return _method_proxy(self, "__long__", *args, **kwargs)

    def __float__(self, *args, **kwargs):
        return _method_proxy(self, "__float__", *args, **kwargs)

    def __complex__(self, *args, **kwargs):
        return _method_proxy(self, "__complex__", *args, **kwargs)

    def __oct__(self, *args, **kwargs):
        return _method_proxy(self, "__oct__", *args, **kwargs)

    def __hex__(self, *args, **kwargs):
        return _method_proxy(self, "__hex__", *args, **kwargs)

    def __index__(self, *args, **kwargs):
        return _method_proxy(self, "__index__", *args, **kwargs)

    def __trunc__(self, *args, **kwargs):
        return _method_proxy(self, "__trunc__", *args, **kwargs)

    def __coerce__(self, *args, **kwargs):
        return _method_proxy(self, "__coerce__", *args, **kwargs)

    def __cmp__(self, *args, **kwargs):
        return _method_proxy(self, "__cmp__", *args, **kwargs)

    def __eq__(self, *args, **kwargs):
        return _method_proxy(self, "__eq__", *args, **kwargs)

    def __ne__(self, *args, **kwargs):
        return _method_proxy(self, "__ne__", *args, **kwargs)

    def __lt__(self, *args, **kwargs):
        return _method_proxy(self, "__lt__", *args, **kwargs)

    def __gt__(self, *args, **kwargs):
        return _method_proxy(self, "__gt__", *args, **kwargs)

    def __le__(self, *args, **kwargs):
        return _method_proxy(self, "__le__", *args, **kwargs)

    def __ge__(self, *args, **kwargs):
        return _method_proxy(self, "__ge__", *args, **kwargs)

    def __pos__(self, *args, **kwargs):
        return _method_proxy(self, "__pos__", *args, **kwargs)

    def __neg__(self, *args, **kwargs):
        return _method_proxy(self, "__neg__", *args, **kwargs)

    def __abs__(self, *args, **kwargs):
        return _method_proxy(self, "__abs__", *args, **kwargs)

    def __invert__(self, *args, **kwargs):
        return _method_proxy(self, "__invert__", *args, **kwargs)

    def __round__(self, *args, **kwargs):
        return _method_proxy(self, "__round__", *args, **kwargs)

    def __floor__(self, *args, **kwargs):
        return _method_proxy(self, "__floor__", *args, **kwargs)

    def __ceil__(self, *args, **kwargs):
        return _method_proxy(self, "__ceil__", *args, **kwargs)

    def __add__(self, *args, **kwargs):
        return _method_proxy(self, "__add__", *args, **kwargs)

    def __sub__(self, *args, **kwargs):
        return _method_proxy(self, "__sub__", *args, **kwargs)

    def __mul__(self, *args, **kwargs):
        return _method_proxy(self, "__mul__", *args, **kwargs)

    def __floordiv__(self, *args, **kwargs):
        return _method_proxy(self, "__floordiv__", *args, **kwargs)

    def __div__(self, *args, **kwargs):
        return _method_proxy(self, "__div__", *args, **kwargs)

    def __truediv__(self, *args, **kwargs):
        return _method_proxy(self, "__truediv__", *args, **kwargs)

    def __mod__(self, *args, **kwargs):
        return _method_proxy(self, "__mod__", *args, **kwargs)

    def __divmod__(self, *args, **kwargs):
        return _method_proxy(self, "__divmod__", *args, **kwargs)

    def __pow__(self, *args, **kwargs):
        return _method_proxy(self, "__pow__", *args, **kwargs)

    def __lshift__(self, *args, **kwargs):
        return _method_proxy(self, "__lshift__", *args, **kwargs)

    def __rshift__(self, *args, **kwargs):
        return _method_proxy(self, "__rshift__", *args, **kwargs)

    def __and__(self, *args, **kwargs):
        return _method_proxy(self, "__and__", *args, **kwargs)

    def __or__(self, *args, **kwargs):
        return _method_proxy(self, "__or__", *args, **kwargs)

    def __xor__(self, *args, **kwargs):
        return _method_proxy(self, "__xor__", *args, **kwargs)

    def __radd__(self, *args, **kwargs):
        return _method_proxy(self, "__radd__", *args, **kwargs)

    def __rsub__(self, *args, **kwargs):
        return _method_proxy(self, "__rsub__", *args, **kwargs)

    def __rmul__(self, *args, **kwargs):
        return _method_proxy(self, "__rmul__", *args, **kwargs)

    def __rfloordiv__(self, *args, **kwargs):
        return _method_proxy(self, "__rfloordiv__", *args, **kwargs)

    def __rdiv__(self, *args, **kwargs):
        return _method_proxy(self, "__rdiv__", *args, **kwargs)

    def __rtruediv__(self, *args, **kwargs):
        return _method_proxy(self, "__rtruediv__", *args, **kwargs)

    def __rmod__(self, *args, **kwargs):
        return _method_proxy(self, "__rmod__", *args, **kwargs)

    def __rdivmod__(self, *args, **kwargs):
        return _method_proxy(self, "__rdivmod__", *args, **kwargs)

    def __rpow__(self, *args, **kwargs):
        return _method_proxy(self, "__rpow__", *args, **kwargs)

    def __rlshift__(self, *args, **kwargs):
        return _method_proxy(self, "__rlshift__", *args, **kwargs)

    def __rrshift__(self, *args, **kwargs):
        return _method_proxy(self, "__rrshift__", *args, **kwargs)

    def __rand__(self, *args, **kwargs):
        return _method_proxy(self, "__rand__", *args, **kwargs)

    def __ror__(self, *args, **kwargs):
        return _method_proxy(self, "__ror__", *args, **kwargs)

    def __rxor__(self, *args, **kwargs):
        return _method_proxy(self, "__rxor__", *args, **kwargs)

    def __iadd__(self, *args, **kwargs):
        object.__setattr__(
            self, "_value", _method_proxy(self, "__add__", *args, **kwargs)
        )
        return self

    def __isub__(self, *args, **kwargs):
        object.__setattr__(
            self, "_value", _method_proxy(self, "__sub__", *args, **kwargs)
        )
        return self

    def __imul__(self, *args, **kwargs):
        object.__setattr__(
            self, "_value", _method_proxy(self, "__mul__", *args, **kwargs)
        )
        return self

    def __ifloordiv__(self, *args, **kwargs):
        object.__setattr__(
            self, "_value", _method_proxy(self, "__floordiv__", *args, **kwargs)
        )
        return self

    def __idiv__(self, *args, **kwargs):
        object.__setattr__(
            self, "_value", _method_proxy(self, "__div__", *args, **kwargs)
        )
        return self

    def __itruediv__(self, *args, **kwargs):
        object.__setattr__(
            self, "_value", _method_proxy(self, "__truediv__", *args, **kwargs)
        )
        return self

    def __imod__(self, *args, **kwargs):
        object.__setattr__(
            self, "_value", _method_proxy(self, "__mod__", *args, **kwargs)
        )
        return self

    def __ipow__(self, *args, **kwargs):
        object.__setattr__(
            self, "_value", _method_proxy(self, "__pow__", *args, **kwargs)
        )
        return self

    def __ilshift__(self, *args, **kwargs):
        object.__setattr__(
            self, "_value", _method_proxy(self, "__lshift__", *args, **kwargs)
        )
        return self

    def __irshift__(self, *args, **kwargs):
        object.__setattr__(
            self, "_value", _method_proxy(self, "__rshift__", *args, **kwargs)
        )
        return self

    def __iand__(self, *args, **kwargs):
        object.__setattr__(
            self, "_value", _method_proxy(self, "__and__", *args, **kwargs)
        )
        return self

    def __ior__(self, *args, **kwargs):
        object.__setattr__(
            self, "_value", _method_proxy(self, "__or__", *args, **kwargs)
        )
        return self

    def __ixor__(self, *args, **kwargs):
        object.__setattr__(
            self, "_value", _method_proxy(self, "__xor__", *args, **kwargs)
        )
        return self
