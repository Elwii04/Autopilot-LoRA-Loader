"""
Flexible input types for dynamic node inputs.
Based on rgthree-comfy's FlexibleOptionalInputType implementation.
"""

from typing import Union


class AnyType(str):
    """A special class that is always equal in not equal comparisons. Credit to pythongosssss"""

    def __ne__(self, __value: object) -> bool:
        return False


class FlexibleOptionalInputType(dict):
    """A special class to make flexible nodes that pass data to our python handlers.

    Enables both flexible/dynamic input types (like for Any Switch) or a dynamic number of inputs
    (like for Any Switch, Context Switch, Context Merge, Power Lora Loader, etc).

    Initially, ComfyUI only needed to return True for `__contains__` below, which told ComfyUI that
    our node will handle the input, regardless of what it is.

    However, after https://github.com/comfyanonymous/ComfyUI/pull/2666 ComfyUI's execution changed
    also checking the data for the key; specifically, the type which is the first tuple entry. This
    type is supplied to our FlexibleOptionalInputType and returned for any non-data key. This can be a
    real type, or use the AnyType for additional flexibility.
    """

    def __init__(self, type, data: Union[dict, None] = None):
        """Initializes the FlexibleOptionalInputType.

        Args:
            type: The flexible type to use when ComfyUI retrieves an unknown key (via `__getitem__`).
            data: An optional dict to use as the basis. This is stored both in a `data` attribute, so we
                can look it up without hitting our overrides, as well as iterated over and adding its key
                and values to our `self` keys. This way, when looked at, we will appear to represent this
                data. When used in an "optional" INPUT_TYPES, these are the starting optional node types.
        """
        self.type = type
        self.data = data
        if self.data is not None:
            for k, v in self.data.items():
                self[k] = v

    def __getitem__(self, key):
        # If we have this key in the initial data, then return it. Otherwise return the tuple with our
        # flexible type.
        if self.data is not None and key in self.data:
            val = self.data[key]
            return val
        return (self.type,)

    def __contains__(self, key):
        """Always contain a key, and we'll always return the tuple above when asked for it."""
        return True


any_type = AnyType("*")
