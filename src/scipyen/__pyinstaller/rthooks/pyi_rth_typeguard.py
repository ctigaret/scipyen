# def _pyi_rthook():
#     has_typeguard_typecheck_instrument=False
#     try:
#         import typeguard._decorators
#         has_typeguard_typecheck_instrument = "instrument" in typeguard._decorators.__dict__
#
#     except:
#         has_typeguard_typecheck_instrument = False
#
#     if has_typeguard_typecheck_instrument:
#         _old_instrument = typeguard._decorators.instrument
#
#         def _instrument(*args):
#             # import sys
#             # a0 = sys.argv.pop(0)
#             try:
#                 return _old_instrument(*args)
#             finally:
#                 return "no code associated"
#
#         typeguard._decorators.instrument = _instrument

def _pyi_rthook():
    """Makes typeguard._decorators.typecheced a NOOP"""
    has_typeguard_typechecked=False
    try:
        import typeguard._decorators
        has_typeguard_typechecked = "typechecked" in typeguard._decorators.__dict__

    except:
        has_typeguard_typechecked = False

    if has_typeguard_typechecked:
        _old_typechecked = typeguard._decorators.typechecked

        def _typechecked(*args):
            target = args[0]
            try:
                return _old_typechecked(*args)
            finally:
                return target


        typeguard._decorators.typechecked = _typechecked



_pyi_rthook()

del _pyi_rthook
