# TODO: Validate
"""Functions to copy function and method parameters from one function to another."""

# Copied from this pull request: https://github.com/python/cpython/pull/121693
from collections.abc import Callable
from typing import Any, Concatenate, cast


def copy_func_params[**Param, RV](
    source_func: Callable[Param, Any],  # noqa: ARG001
) -> Callable[[Callable[..., RV]], Callable[Param, RV]]:
    """Cast the decorated function's call signature to the source_func's.

    Use this decorator enhancing an upstream function while keeping its
    call signature.
    Returns the original function with the source_func's call signature.
    Usage::
        from typing import copy_func_params, Any
        def upstream_func(a: int, b: float, *, double: bool = False) -> float:
            ...
        @copy_func_params(upstream_func)
        def enhanced(
            a: int, b: float, *args: Any, double: bool = False, **kwargs: Any
        ) -> str:
            ...
    .. note::
       Include ``*args`` and ``**kwargs`` in the signature of the decorated
       function in order to avoid TypeErrors when the call signature of
       *source_func* changes.
    """

    def return_func(func: Callable[..., RV]) -> Callable[Param, RV]:
        return cast("Callable[Param, RV]", func)

    return return_func


def copy_method_params[**Param, Arg1, RV](
    source_method: Callable[Concatenate[Any, Param], Any],  # noqa: ARG001
) -> Callable[
    [Callable[Concatenate[Arg1, ...], RV]],
    Callable[Concatenate[Arg1, Param], RV],
]:
    """Cast the decorated method's call signature to the source_method's.

    Same as :func:`copy_func_params` but intended to be used with methods.
    It keeps the first argument (``self``/``cls``) of the decorated method.
    """

    def return_func(
        func: Callable[Concatenate[Arg1, ...], RV],
    ) -> Callable[Concatenate[Arg1, Param], RV]:
        return cast("Callable[Concatenate[Arg1, Param], RV]", func)

    return return_func
