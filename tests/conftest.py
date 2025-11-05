import warnings

warnings.filterwarnings(
    "ignore",
    message=r"builtin type .* has no __module__ attribute",
    category=DeprecationWarning,
)
