# SPDX-FileCopyrightText: 2024 Cezar M. Tigaret <cezar.tigaret@gmail.com>
# SPDX-License-Identifier: GPL-3.0-or-later
# SPDX-License-Identifier: LGPL-2.1-or-later

# TODO 2026-05-07 21:45:55 finalize me !
from abc import ABC
import typing
from neo.core.objectlist import ObjectList as NeoObjectList
from core.scipyendataclasses import ScipyenDataclass

class ElectrophysiologyProtocol(ABC):
    r"""Abstract base class for electrophysiology data acquisition protocols

    """
    def __init__(self, **kwargs):
        pass
        # self._nADCChannels_ = kwargs.get("nADCChannels",0)
        # self._nDACChannels_ = kwargs.get("nDACChannels",0)
        # self._nDigitalOutputs_ = kwargs.get("nDigitalOutputs", 0)
        # self._nTotalDigitalOutputs_ = kwargs.get("nTotalDigitalOutputs",0)
        # self._activeDACChannel_= kwargs.get("activeDACChannel", 0)
        # self._hasAltDacOutState_ = kwargs.get("altDACOutState",False)

    # TODO 2023-10-15 21:10:06 on backburner for now.
    # write subclasses for:
    # • CED Signal protocols ("configuration")
    # • other ephys acquisition software (CED Spike, ephus?)

#     def __init__(self):
#         # possible values for self._data_source_:
#         # "Axon", "CEDSignal", "CEDSpike", "Ephus", "NA", "unknown"
#         # default: "unknown"
#         self._data_source_ = "unknown"
#         self._acquisition_protocol_ = dict()
#         self._acquisition_protocol_["trigger_protocol"] = TriggerProtocol()
#         self._averaged_runs_ = False
#         self._alternative_DAC_command_output_ = False
#         self._alternative_digital_outputs_ = False
#
#     def parse_data(self, data:neo.Block, metadata:dict=None):
#         if hasattr(data, "annotations"):
#             self._data_source_ = data.annotations.get("software", "unknown")
#             if self._data_source_ == "Axon":
#                 self._parse_axon_data_(data, metadata)
#
#             else:
#                 # TODO 2020-02-20 11:32:16
#                 # parse CEDSignal, CEDSpike, EPhus, unknown
#                 pass
#
#     def _parse_axon_data_(self, data:neo.Block, metadata:dict=None):
#         data_protocol = data.annotations.get("protocol", None)
#
#         self._averaged_runs_ = data_protocol.get("lRunsPerTrial",1) > 1
#         self._n_sweeps_ = data_protocol.get("lEpisodesPerRun",1)
#         self._alternative_digital_outputs_ = data_protocol.get("nAlternativeDigitalOutputState", 0) == 1
#         self._alternative_DAC_command_output_ = data_protocol.get("nAlternativeDACOutputState", 0) == 1
#
#     def _parse_ced_data_(self, data:object):
#         pass

class ProtocolList(NeoObjectList):
    allowed_contents = (ElectrophysiologyProtocol, )

    def __init__(self, *items, name: str | None = None, parent: object = None):
        self.name = "" if not isinstance(name, str) else name
        self._items = []

        if len(items):
            if len(items) == 1 and isinstance(items[0], typing.Iterable):
                items = list(items[0])

            if any(
                not isinstance(i, self.allowed_contents)
                or not any(type(i).__name__ in n for n in (t.__name__ for t in self.allowed_contents)) # list(map(lambda t: t.__name__, self.allowed_contents)))
                # or not any(type(i).__name__ in n for n in list(map(lambda t: t.__name__, self.allowed_contents)))
                for i in items):
                raise TypeError(f"Can only contain {self.allowed_contents[0].__name__} objects, not {type(item).__name__}")

            self._items = list(items)

        if parent is not None and ScipyenDataclass not in inspect.getmro(type(parent)):
            raise TypeError(f"Parent must be a ScipyenDataclass or None; got {type(parent).__name__} instead")

        self._parent = parent

    @property
    def parent(self) -> ScipyenDataclass | None:
        return self._parent

    @parent.setter
    def parent(self, obj: ScipyenDataclass | None = None):
        if isinstance(obj, ScipyenDataclass):
            self._parent = obj
        else:
            self._parent = None

    def __contains__(self, obj: ElectrophysiologyProtocol):
        if isinstance(obj, self.allowed_contents):
            return any(next(utilities.approximatelyEqual(obj, p)) for p in self._items)
        return False

    def __iter__(self):
        """Implements ``iter(self)``"""
        yield from self._items

    def __delitem__(self, i: int) -> None:
        if len(self._items) == 0:
            return

        if i < len(self._items) and i >= -len(self._items):
            del(self._items[i])
        else:
            raise IndexError(f"Index {i} out of range for {len(self._items)} items")

    def __getitem__(self, i: int | slice| str) -> ElectrophysiologyProtocol | None:
        """``x.__getitem__(y)`` implements the indexing statement ``x[y]``"""
        if len(self._items) == 0:
            raise IndexError(f"Index {i} out of range for {len(self._items)} items")

        if isinstance(i, int):
            if i < len(self._items) and i >= -len(self._items):
                return self._items[i]

            else:
                raise IndexError(f"Index {i} out of range for {len(self._items)} items")

        elif isinstance(i, slice):
            return self._items[i]

        elif isinstance(i, str):
            found = [x for x in filter(lambda x: x.name == i, self._items)]

            if len(found) == 0:
                raise IndexError("A pathway named '{i}' does not exist")

            if len(found) == 1:
                return found[0]

            return found

    def __setitem__(self, i: int, value: ElectrophysiologyProtocol):
        if not isinstance(value, self.allowed_contents):
            raise TypeError(f"Can only contain {self.allowed_contents[0].__name__} objects, not {type(value).__name__}")

        if not isinstance(i, int):
            raise TypeError("Elements can only be assigned through integer indexing")

        if len(self._items) == 0:
            raise ValueError(f"Index {i} out of range for {len(self._items)} items")

        if i < len(self._items) and i >= -len(self._items):
            self._items[i] = value

        else:
            raise IndexError(f"Index {i} out of range for {len(self._items)} items")

    def __str__(self):
        """Return str(self)"""
        return f"<{self.__class__.__name__}> with {len(self._items)} {self.allowed_contents[0].__name__} objects"

    def __repr__(self):
        header = f"<{self.__class__.__name__}>"
        if isinstance(self.name, str) and len(self.name.strip()):
            header += f" '{self.name}'"

        s = [f"{header} with {len(self._items)} {self.allowed_contents[0].__name__} objects",
            ]

        if len(self._items):
            s[0]+= ":"
            s.extend([f"{ki}: {i}" for ki, i in enumerate(self._items)])
            # s.extend(list(map(lambda p: f"{p[0]}: {p[1]}", enumerate(self._items))))

        return "\n".join(s)

    def __len__(self):
        """Return len(self)"""
        return len(self._items)

    def _add_items(self, other: typing.Self, in_place=False) -> typing.Self:
        self._items = self._items + other._items
        return self

    def __add__(self, other):
        """Return self + other"""
        ret = self.__class__(self._items, parent=self.parent)
        if isinstance(other, self.__class__):
            return ret._add_items(other)

        elif isinstance(other, self.allowed_contents):
            ret._items.append(other)
            return ret

        elif (isinstance(other, typing.Sequence)
              and all(isinstance(o, self.allowed_contents) for o in other)):
            ret._items.extend(list(other))
            return ret

        else:
            return ret

    def __iadd__(self, other):
        """Return self"""
        if isinstance(other, self.__class__):
            return self._add_items(other, in_place=True)

        elif isinstance(other, self.allowed_contents):
            self._items.append(other)
            return self

        elif (isinstance(other, typing.Sequence)
              and all(isinstance(o, self.allowed_contents) for o in other)):
            self._items.extend(list(other))
            return self

        else:
            return self

    def __radd__(self, other):
        """Return other + self"""
        ret = self.__class__(self._items, parent=self.parent)
        if isinstance(other, self.__class__):
            return other._add_items(ret)

        elif isinstance(other, self.allowed_contents):
            ret._items.append(other)
            return ret

        elif (isinstance(other, typing.Sequence)
              and all(isinstance(o, self.allowed_contents) for o in other)):
            ret._items.extend(list(other))
            return ret
        else:
            return ret

    def append(self, obj):
        """
        Appends a ElectrophysiologyProtocol

        Parameters
        ----------
        obj: ElectrophysiologyProtocol

        """
        # print(f"{self.__class__.__name__}.append({obj})")
        if not isinstance(obj, self.allowed_contents):
            raise TypeError(f"Can only append {self.allowed_contents[0].__name__} objects")
        self._items.append(obj)

    def extend(self, iterable):
        """Extends with additional ElectrophysiologyProtocol objects from an iterable

        Parameters
        ----------
        iterable: iterable[ElectrophysiologyProtocol]

        """
        if all (isinstance(o, self.allowed_contents) for o in iterable):
            self._items.extend(iterable)
        else:
            raise TypeError(f"Can only append {self.allowed_contents[0].__name__} objects")

    def insert(self, index:int, obj: object):
        if isinstance(obj, self.allowed_contents):
            self._items.insert(index, obj)
        else:
            raise TypeError(f"Can only insert {self.allowed_contents[0].__name__} objects")

    def clear(self):
        self._items.clear()

    def pop(self, index: int = -1, /,) -> object:
        return self._items.pop(index)

    def remove(self, obj:object):
        self._items.remove(obj)

    def reverse(self):
        return self.__class__(reversed(self._items))

    def count(self, obj) -> int:
        return self._items.count(obj)

    def index(self, *args):
        return self._index(*args)
