from collections.abc import Callable

from thunder.core.langctxs import LanguageContext, register_langctx, Languages, resolve_language
from thunder.core.pytree import tree_flatten
from thunder.core.proxies import TensorProxy, NumberProxy

#
# Creates and registers the torch language context
#
# NOTE That this is done separately from the definition of thunder.torch operations, because the
#   language context must be available before those operations are defined

_method_name_to_fn_map: dict[str, Callable] = {}


# Creates and registers the core language language context
class ClangCtx(LanguageContext):
    def __init__(self):
        super().__init__("core")

    def has_method(self, id: str) -> bool:
        return id in _method_name_to_fn_map

    def get_method(self, id: str, *args, **kwargs) -> Callable:
        # Note: concrete implmenetations should only raise AttributeError or
        #       return None for "missing" methods as the proxies will
        #       route __getattr__ to here and hasattr relies on __getattr__
        #       throwing AttributeError (only) when the attribute does
        #       not exist.
        inps, _ = tree_flatten((args, kwargs))

        has_proxy_input: bool = False
        for x in inps:
            if isinstance(x, TensorProxy) or isinstance(x, NumberProxy):
                has_proxy_input = True
                break

        if has_proxy_input:
            method: None | Callable = _method_name_to_fn_map.get(id, None)
            if method is None:
                raise AttributeError(f"The {self.name} language context has no method {id}")
            return method

        # has_proxy_input is False
        # Defers to the primitive language context when there are no tensor inputs=
        #   (the primitive language context handles operations on numbers)
        primsctx: LanguageContext = resolve_language(Languages.PRIMS)
        if not primsctx.has_method(id):
            raise AttributeError(
                f"Attempting to call method {id} in the core language context, but it has no tensor inputs and the primitive language context (which handles numbers) doesn't have the method"
            )
        prim_method: Callable = primsctx.get_method(id, *args, **kwargs)
        return prim_method


clangctx = ClangCtx()
register_langctx(Languages.CLANG, clangctx)


# Registers a method with the torch language context
def register_method(method_name: str, method: Callable, /) -> None:
    _method_name_to_fn_map[method_name] = method
