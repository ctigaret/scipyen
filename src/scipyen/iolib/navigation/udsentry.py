# -*- coding: utf-8 -*-
# SPDX-FileCopyrightText: 2025 Cezar M. Tigaret <cezar.tigaret@gmail.com>
# SPDX-License-Identifier: GPL-3.0-or-later
# SPDX-License-Identifier: LGPL-2.1-or-later

"""
"""
import sys, os, typing, pathlib, stat, io
# from collections import namedtuple
import dataclasses
from enum import IntEnum
from qtpy import QtCore, QtGui, QtWidgets, QtSvg
from qtpy.QtCore import Signal, Slot, Property
from qtpy.uic import loadUiType as __loadUiType__
from core.prog import safeWrapper
from core.sysutils import adapt_ui_path
from . import utils
HAS_STATX = False
try:
    from . import statx
    HAS_STATX = True
    stat_result = statx.stat_result
except:
    stat_result = os.stat_result

__module_path__ = os.path.abspath(os.path.dirname(__file__))

class ItemTypes(IntEnum):
    """Bit field used to specify the item type of a StandardFieldTypes. """
    UDS_STRING  = 0x01000000
    UDS_NUMBER  = 0x02000000
    UDS_TIME    = 0x04000000 | UDS_NUMBER

class StandardFieldTypes(IntEnum):
    """
        Constants used to specify the type of a UDSEntry’s field. 

        UDS_SIZE Size of the file. 

        UDS_USER User Name of the file owner Not present on local fs, use 
            UDS_LOCAL_USER_ID. 

        UDS_ICON_NAME Name of the icon, that should be used for displaying. It 
            overrides all other detection mechanisms 

        UDS_GROUP Group Name of the file owner Not present on local fs, use 
            UDS_LOCAL_GROUP_ID. 

        UDS_NAME Filename - as displayed in directory listings etc. "." has the 
            usual special meaning of "current directory" UDS_NAME must always be
            set and never be empty, neither contain '/'. Note that KIO will append
            the UDS_NAME to the url of their parent directory, so all KIO workers 
            must use that naming scheme ("url_of_parent/filename" will be the full 
            url of that file). To customize the appearance of files without changing 
            the url of the items, use UDS_DISPLAY_NAME. 

        UDS_LOCAL_PATH A local file path if the KIO worker display files sitting 
            on the local filesystem (but in another hierarchy, e.g. settings:/ 
            or remote:/) 

        UDS_HIDDEN Treat the file as a hidden file (if set to 1) or as a normal 
            file (if set to 0). This field overrides the default behavior (the 
            check for a leading dot in the filename). 

        UDS_ACCESS Access permissions (part of the mode returned by stat) 

        UDS_MODIFICATION_TIME The last time the file was modified. Required time 
            format: seconds since UNIX epoch. 

        UDS_ACCESS_TIME The last time the file was opened. Required time format: 
            seconds since UNIX epoch. 

        UDS_CREATION_TIME The time the file was created. Required time format: 
            seconds since UNIX epoch. 

        UDS_FILE_TYPE File type, part of the mode returned by stat (for a link, 
            this returns the file type of the pointed item) check UDS_LINK_DEST 
            to know if this is a link. 

        UDS_LINK_DEST Name of the file where the link points to Allows to check 
            for a symlink (don't use S_ISLNK !) 

        UDS_URL An alternative URL (If different from the caption). Can be used 
            to mix different hierarchies. Use UDS_DISPLAY_NAME if you simply want 
            to customize the user-visible filenames, or use UDS_TARGET_URL if you 
            want "links" to unrelated urls. 

        UDS_MIME_TYPE A MIME type; the KIO worker should set it if it's known. 

        UDS_GUESSED_MIME_TYPE A MIME type to be used for displaying only. But 
            when 'running' the file, the MIME type is re-determined This is for 
            special cases like symlinks in FTP; you probably don't want to use 
            this one. 

        UDS_XML_PROPERTIES XML properties, e.g. for WebDAV. 

        UDS_EXTENDED_ACL Indicates that the entry has extended ACL entries. 

        UDS_ACL_STRING The access control list serialized into a single string. 

        UDS_DEFAULT_ACL_STRING The default access control list serialized into a 
            single string. Only available for directories. 

        UDS_DISPLAY_NAME If set, contains the label to display instead of the 
        'real name' in UDS_NAME.

        UDS_TARGET_URL This file is a shortcut or mount, pointing to an URL in a 
            different hierarchy.

        UDS_DISPLAY_TYPE User-readable type of file (if not specified, the MIME 
            type's description is used)

        UDS_ICON_OVERLAY_NAMES A comma-separated list of supplementary icon 
            overlays which will be added to the list of overlays created by
            KFileItem. 

        UDS_COMMENT A comment which will be displayed as is to the user. The 
            string value may contain plain text or Qt-style rich-text extensions. 

        UDS_DEVICE_ID Device number for this file, used to detect hardlinks. 

        UDS_INODE Inode number for this file, used to detect hardlinks. 

        UDS_RECURSIVE_SIZE For folders, the recursize size of its content. 

        UDS_LOCAL_USER_ID User ID of the file owner.

        UDS_LOCAL_GROUP_ID Group ID of the file owner.

        UDS_EXTRA Extra data (used only if you specified Columns/ColumnsTypes) 
            NB: you cannot repeat this entry; use UDS_EXTRA + i until UDS_EXTRA_END. 

        UDS_EXTRA_END Extra data (used only if you specified 
            Columns/ColumnsTypes) NB: you cannot repeat this entry; use UDS_EXTRA + i until UDS_EXTRA_END. 
    """
    UDS_SIZE                =   1 | ItemTypes.UDS_NUMBER
    UDS_SIZE_LARGE          =   2 | ItemTypes.UDS_NUMBER
    UDS_USER                =   3 | ItemTypes.UDS_STRING
    UDS_ICON_NAME           =   4 | ItemTypes.UDS_STRING
    UDS_GROUP               =   5 | ItemTypes.UDS_STRING
    UDS_NAME                =   6 | ItemTypes.UDS_STRING
    UDS_LOCAL_PATH          =   7 | ItemTypes.UDS_STRING
    UDS_HIDDEN              =   8 | ItemTypes.UDS_NUMBER
    UDS_ACCESS              =   9 | ItemTypes.UDS_NUMBER
    UDS_MODIFICATION_TIME   =  10 | ItemTypes.UDS_TIME
    UDS_ACCESS_TIME         =  11 | ItemTypes.UDS_TIME
    UDS_CREATION_TIME       =  12 | ItemTypes.UDS_TIME
    UDS_FILE_TYPE           =  13 | ItemTypes.UDS_NUMBER
    UDS_LINK_DEST           =  14 | ItemTypes.UDS_STRING
    UDS_URL                 =  15 | ItemTypes.UDS_STRING
    UDS_MIME_TYPE           =  16 | ItemTypes.UDS_STRING
    UDS_GUESSED_MIME_TYPE   =  17 | ItemTypes.UDS_STRING
    UDS_XML_PROPERTIES      =  18 | ItemTypes.UDS_STRING
    UDS_EXTENDED_ACL        =  19 | ItemTypes.UDS_NUMBER
    UDS_ACL_STRING          =  20 | ItemTypes.UDS_STRING
    UDS_DEFAULT_ACL_STRING  =  21 | ItemTypes.UDS_STRING
    UDS_DISPLAY_NAME        =  22 | ItemTypes.UDS_STRING
    UDS_TARGET_URL          =  23 | ItemTypes.UDS_STRING
    UDS_DISPLAY_TYPE        =  24 | ItemTypes.UDS_STRING
    UDS_ICON_OVERLAY_NAMES  =  25 | ItemTypes.UDS_STRING
    UDS_COMMENT             =  26 | ItemTypes.UDS_STRING
    UDS_DEVICE_ID           =  27 | ItemTypes.UDS_NUMBER
    UDS_INODE               =  28 | ItemTypes.UDS_NUMBER
    UDS_RECURSIVE_SIZE      =  29 | ItemTypes.UDS_NUMBER
    UDS_LOCAL_USER_ID       =  30 | ItemTypes.UDS_NUMBER
    UDS_LOCAL_GROUP_ID      =  31 | ItemTypes.UDS_NUMBER
    UDS_EXTRA               = 100 | ItemTypes.UDS_STRING
    UDS_EXTRA_END           = 140 | ItemTypes.UDS_STRING
    
@dataclasses.dataclass
class Field:
    # NOTE: 2025-01-04 23:08:49
    # LLONG_MIN is -sys.maxsize-1
    m_index:int = dataclasses.field(default_factory = int)
    m_long:typing.Optional[int] = dataclasses.field(default = -sys.maxsize-1)
    m_str:typing.Optional[str] = dataclasses.field(default_factory = str)
    
    def __init__(self, index:int, value:typing.Union[str, int]=0):
        if not isinstance(index, int):
            raise TypeError(f"First argument ('index') must be an int; instead, got {type(index).__name__}")
        self.m_index = index
        if isinstance(value, int):
            self.m_long = value
            self.m_str = str()
        elif isinstance(value, str):
            self.m_long = -sys.maxsize-1
            self.m_str = value
    
class _UDSEntryPrivate_:
    # ### BEGIN Fields
    UDS_STRING:int              =  ItemTypes.UDS_STRING
    UDS_NUMBER:int              =  ItemTypes.UDS_NUMBER
    UDS_TIME:int                =  ItemTypes.UDS_TIME
    UDS_SIZE:int                =  StandardFieldTypes.UDS_SIZE                
    UDS_SIZE_LARGE:int          =  StandardFieldTypes.UDS_SIZE_LARGE          
    UDS_USER:int                =  StandardFieldTypes.UDS_USER                
    UDS_ICON_NAME:int           =  StandardFieldTypes.UDS_ICON_NAME           
    UDS_GROUP:int               =  StandardFieldTypes.UDS_GROUP               
    UDS_NAME:int                =  StandardFieldTypes.UDS_NAME                
    UDS_LOCAL_PATH:int          =  StandardFieldTypes.UDS_LOCAL_PATH          
    UDS_HIDDEN:int              =  StandardFieldTypes.UDS_HIDDEN              
    UDS_ACCESS:int              =  StandardFieldTypes.UDS_ACCESS
    UDS_MODIFICATION_TIME:int   =  StandardFieldTypes.UDS_MODIFICATION_TIME
    UDS_ACCESS_TIME:int         =  StandardFieldTypes.UDS_ACCESS_TIME         
    UDS_CREATION_TIME:int       =  StandardFieldTypes.UDS_CREATION_TIME       
    UDS_FILE_TYPE:int           =  StandardFieldTypes.UDS_FILE_TYPE           
    UDS_LINK_DEST:int           =  StandardFieldTypes.UDS_LINK_DEST           
    UDS_URL:int                 =  StandardFieldTypes.UDS_URL                 
    UDS_MIME_TYPE:int           =  StandardFieldTypes.UDS_MIME_TYPE           
    UDS_GUESSED_MIME_TYPE:int   =  StandardFieldTypes.UDS_GUESSED_MIME_TYPE   
    UDS_XML_PROPERTIES:int      =  StandardFieldTypes.UDS_XML_PROPERTIES      
    UDS_EXTENDED_ACL:int        =  StandardFieldTypes.UDS_EXTENDED_ACL        
    UDS_ACL_STRING:int          =  StandardFieldTypes.UDS_ACL_STRING          
    UDS_DEFAULT_ACL_STRING:int  =  StandardFieldTypes.UDS_DEFAULT_ACL_STRING  
    UDS_DISPLAY_NAME:int        =  StandardFieldTypes.UDS_DISPLAY_NAME        
    UDS_TARGET_URL:int          =  StandardFieldTypes.UDS_TARGET_URL          
    UDS_DISPLAY_TYPE:int        =  StandardFieldTypes.UDS_DISPLAY_TYPE        
    UDS_ICON_OVERLAY_NAMES:int  =  StandardFieldTypes.UDS_ICON_OVERLAY_NAMES  
    UDS_COMMENT :int            =  StandardFieldTypes.UDS_COMMENT             
    UDS_DEVICE_ID:int           =  StandardFieldTypes.UDS_DEVICE_ID           
    UDS_INODE:int               =  StandardFieldTypes.UDS_INODE               
    UDS_RECURSIVE_SIZE:int      =  StandardFieldTypes.UDS_RECURSIVE_SIZE      
    UDS_LOCAL_USER_ID:int       =  StandardFieldTypes.UDS_LOCAL_USER_ID       
    UDS_LOCAL_GROUP_ID:int      =  StandardFieldTypes.UDS_LOCAL_GROUP_ID      
    UDS_EXTRA:int               =  StandardFieldTypes.UDS_EXTRA               
    UDS_EXTRA_END:int           =  StandardFieldTypes.UDS_EXTRA_END           
    
    Field = Field
    
    def __init__(self):
        self.storage = list()
        self.cachedStrings = list()
        
    def clear(self):
        # void clear();
        self.storage.clear()
        self.cachedStrings.clear()
    
    def count(self) -> int:
        return len(self.storage)
        
    def contains(self, udsField:int) -> bool:
        # bool contains(uint udsField) const;
        return udsField in self.fields()
    
    def stringValue(self, udsField:int) -> str:
        # QString stringValue(uint udsField) const;
        # indexes = list(map(lambda x: x.m_index, self.storage))
        indexes = self.fields()
        if udsField in indexes:
            return self.storage[indexes.index(udsField)].m_str
        return str()

    def numberValue(self, udsField:int, defaultValue:int = -1) -> int:
        # long long numberValue(uint udsField, long long defaultValue = -1) const;
        indexes = list(map(lambda x: x.m_index, self.storage))
        if udsField in indexes:
            return self.storage[indexes.index(udsField)].m_long
        return defaultValue
    
    def fields(self) -> list[int]:
        # QList<uint> fields() const;
        return list(map(lambda x: x.m_index, filter(lambda x: isinstance(x, Field), self.storage)))
    
    def reserve(self, size:int): 
        # self.storage = [None] * size
        self.cachedStrings = [None] * size
    
    def insert(self, udsField:int, value:typing.Union[str, int]):
        """Appends a Field with a UDS_STRING type of index (udsField) to the internal storage.
        Does nothing if such a field exists in the storage
        """
        # void insert(uint udsField, const QString &value);
        # void insert(uint udsField, long long value);
        
        # NOTE: 2025-01-04 23:34:08
        # Check that the value of udsField is one of the values in 
        # StandardFieldTypes with type ItemTypes.UDS_STRING (for string values)
        # or ItemTypes.UDS_STRING (for int — i.e., long long — value)
        #
        # e.g.:
        #
        # assert(udsentry.StandardFieldTypes.UDS_ICON_NAME & udsentry.ItemTypes.UDS_STRING)
        # >>> is OK
        #
        # but:
        #
        # assert(udsentry.StandardFieldTypes.UDS_FILE_TYPE & udsentry.ItemTypes.UDS_STRING)
        # >>> AssertionError
        #
        # Same goes for 
        # assert(3 & udsentry.ItemTypes.UDS_STRING)
        # >>> AssertionError
        #
        assert isinstance(value, (int, str)), f"'value' expected to be an int or str; instead got {type(value).__name__}"
        if isinstance(value, str):
            assert isinstance(udsField, int) and udsField & ItemTypes.UDS_STRING, "Expecting a StandardFieldTypes value of type ItemTypes.UDS_STRING"
        else:
            assert isinstance(udsField, int) and udsField & ItemTypes.UDS_NUMBER, "Expecting a StandardFieldTypes value of type ItemTypes.UDS_NUMBER"
        # NOTE: skip if there is a Field in 'storage' that has this udsField value as m_index
        # if udsField not in list(map(lambda x: x.m_index, self.storage)):
        # if udsField not in self.fields():
        if not self.contains(udsField):
            self.storage.append(Field(udsField, value))
    
    def replace(self, udsField:int, value:typing.Union[str, int]):
        # void replace(uint udsField, const QString &value);
        # void replace(uint udsField, long long value);
        
        assert isinstance(value, (int, str)), f"'value' expected to be an int or str; instead got {type(value).__name__}"
        if isinstance(value, str):
            assert isinstance(udsField, int) and udsField & ItemTypes.UDS_STRING, "Expecting a StandardFieldTypes value of type ItemTypes.UDS_STRING"
        else:
            assert isinstance(udsField, int) and udsField & ItemTypes.UDS_NUMBER, "Expecting a StandardFieldTypes value of type ItemTypes.UDS_NUMBER"
        
        # check if a Field with this udsField as m_index exists in storage
        # indexes = list(map(lambda x: x.m_index, self.storage))
        indexes = self.fields()
        
        if udsField not in indexes:
            self.storage.append(Field(udsField, value))
            return
        
        ndx = indexes.index(udsField)
        if isinstance(value, str):
            self.storage[ndx].m_str = value
        elif isinstance(value, int):
            self.storage[ndx].m_long = value
        else:
            raise TypeError(f"'value' expected to be a str or int; instead got {type(value).__name__}")
        
    def save(self, s:QtCore.QDataStream): 
        # void save(QDataStream &s) const;
        # NOTE: 2025-01-05 15:11:24
        # PyQt5.QtCore.QDataStream has:
        # • convenience read* & write* methods tailored for various fundamental 
        #   data types (see their usage in this method)
        # • methods implementing the C++ "<<" and ">>" stream operators; HOWEVER, 
        #   these expect QByteArray data on the rhs, thus requiring 
        #   packing/upnacking via the struct module!
        #
        s.writeUInt32(len(self.storage))
        for field in self.storage:
            uds = field.m_index
            s.writeUInt32(uds)
            
            if uds & ItemTypes.UDS_STRING:
                s.writeQString(field.m_str) # WARNING: 2025-01-05 15:08:40 writeString expects bytes; writeQString expects str !!!
            elif uds & ItemTypes.UDS_NUMBER:
                s.writeInt64(field.m_long) # NOTE: 2025-01-05 15:09:29 m_long is a long long i.e. a qint64 (signed 64-bit)
            else:
                raise ValueError(f"Found a field with an invalid type: {uds}")
    
    def load(self, s:QtCore.QDataStream): 
        # void load(QDataStream &s);
        # NOTE: 2025-01-05 15:19:22 see:
        #   NOTE: 2025-01-05 15:11:24, 
        #   WARNING: 2025-01-05 15:08:40, 
        #   NOTE: 2025-01-05 15:09:29
        
        self.clear()
        size = s.readUInt32() # needed below...
        self.reserve(size)
        for k in range(size):
            uds = s.readUInt32()
            
            if uds & ItemTypes.UDS_STRING:
                val = s.readQString()
                if val != self.cachedStrings[k]:
                    self.cachedStrings[k] = val
                    
                self.insert(uds, self.cachedStrings[k])
                
            elif uds & ItemTypes.UDS_NUMBER:
                val = s.readInt64()
                self.insert(uds, val)
                
            else:
                raise ValueError(f"Found a field with an invalid type: {uds}")
    
    def debugUDSEntry(self, s:typing.Optional[io.TextIOBase]=None):
        # void debugUDSEntry(QDebug &stream) const;
        ret = list("[")
        for field in self.storage:
            fld = f"Field: {self.nameOfUdsField(field.m_index)} = "
            if field.m_index & ItemTypes.UDS_STRING:
                fld += f"{field.m_str}"
            elif field.m_index & ItemTypes.UDS_NUMBER:
                fld += f"{field.m_long}"
            else:
                raise ValueError(f"Found a field with an invalid type: {uds}")
            
            ret.append(fld)
        ret.append("]")
        
        if isinstance(s, io.TextIOBase):
            print("\n".join(ret), file=s, flush=True)
        else:
            print("\n".join(ret), flush=True)
    
    @staticmethod
    def nameOfUdsField(field:int) -> str:
        # /**
        #  * @param field numeric UDS field id
        #  * @return the name of the field
        #  */
        # static QString nameOfUdsField(uint field);
        match  field:
            case StandardFieldTypes.UDS_SIZE:
                return "UDS_SIZE"
            case StandardFieldTypes.UDS_SIZE_LARGE:
                return "UDS_SIZE_LARGE"
            case StandardFieldTypes.UDS_USER:
                return "UDS_USER"
            case StandardFieldTypes.UDS_ICON_NAME:
                return "UDS_ICON_NAME"
            case StandardFieldTypes.UDS_GROUP:
                return "UDS_GROUP"
            case StandardFieldTypes.UDS_NAME:
                return "UDS_NAME"
            case StandardFieldTypes.UDS_LOCAL_GROUP_ID:
                return "UDS_LOCAL_GROUP_ID"
            case StandardFieldTypes.UDS_LOCAL_USER_ID:
                return "UDS_LOCAL_USER_ID"
            case StandardFieldTypes.UDS_LOCAL_PATH:
                return "UDS_LOCAL_PATH"
            case StandardFieldTypes.UDS_HIDDEN:
                return "UDS_HIDDEN"
            case StandardFieldTypes.UDS_ACCESS:
                return "UDS_ACCESS"
            case StandardFieldTypes.UDS_MODIFICATION_TIME:
                return "UDS_MODIFICATION_TIME"
            case StandardFieldTypes.UDS_ACCESS_TIME:
                return "UDS_ACCESS_TIME"
            case StandardFieldTypes.UDS_CREATION_TIME:
                return "UDS_CREATION_TIME"
            case StandardFieldTypes.UDS_FILE_TYPE:
                return "UDS_FILE_TYPE"
            case StandardFieldTypes.UDS_LINK_DEST:
                return "UDS_LINK_DEST"
            case StandardFieldTypes.UDS_URL:
                return "UDS_URL"
            case StandardFieldTypes.UDS_MIME_TYPE:
                return "UDS_MIME_TYPE"
            case StandardFieldTypes.UDS_GUESSED_MIME_TYPE:
                return "UDS_GUESSED_MIME_TYPE"
            case StandardFieldTypes.UDS_XML_PROPERTIES:
                return "UDS_XML_PROPERTIES"
            case StandardFieldTypes.UDS_EXTENDED_ACL:
                return "UDS_EXTENDED_ACL"
            case StandardFieldTypes.UDS_ACL_STRING:
                return "UDS_ACL_STRING"
            case StandardFieldTypes.UDS_DEFAULT_ACL_STRING:
                return "UDS_DEFAULT_ACL_STRING"
            case StandardFieldTypes.UDS_DISPLAY_NAME:
                return "UDS_DISPLAY_NAME"
            case StandardFieldTypes.UDS_TARGET_URL:
                return "UDS_TARGET_URL"
            case StandardFieldTypes.UDS_DISPLAY_TYPE:
                return "UDS_DISPLAY_TYPE"
            case StandardFieldTypes.UDS_ICON_OVERLAY_NAMES:
                return "UDS_ICON_OVERLAY_NAMES"
            case StandardFieldTypes.UDS_COMMENT:
                return "UDS_COMMENT"
            case StandardFieldTypes.UDS_DEVICE_ID:
                return "UDS_DEVICE_ID"
            case StandardFieldTypes.UDS_INODE:
                return "UDS_INODE"
            case StandardFieldTypes.UDS_EXTRA:
                return "UDS_EXTRA"
            case StandardFieldTypes.UDS_EXTRA_END:
                return "UDS_EXTRA_END"
            case _:
                return f"Unknown uds field {field}"

class UDSEntry:
    """Usage example:
        from iolib.navigation.udsentry import UDSEntry
        path = pathlib.Path("myFile.dat")
        # ATTENTION : Always use absolute pathlib Path objects!
        buff = os.stat(path.absolute())
        entry = UDSEntry(buff, path.absolute().name)
        entry.stringValue(entry.UDS_NAME)
        >>> 'myFile.dat'
    """
    # ### BEGIN Fields
    UDS_STRING:int              =  ItemTypes.UDS_STRING
    UDS_NUMBER:int              =  ItemTypes.UDS_NUMBER
    UDS_TIME:int                =  ItemTypes.UDS_TIME
    UDS_SIZE:int                =  StandardFieldTypes.UDS_SIZE                
    UDS_SIZE_LARGE:int          =  StandardFieldTypes.UDS_SIZE_LARGE          
    UDS_USER:int                =  StandardFieldTypes.UDS_USER                
    UDS_ICON_NAME:int           =  StandardFieldTypes.UDS_ICON_NAME           
    UDS_GROUP:int               =  StandardFieldTypes.UDS_GROUP               
    UDS_NAME:int                =  StandardFieldTypes.UDS_NAME                
    UDS_LOCAL_PATH:int          =  StandardFieldTypes.UDS_LOCAL_PATH          
    UDS_HIDDEN:int              =  StandardFieldTypes.UDS_HIDDEN              
    UDS_ACCESS:int              =  StandardFieldTypes.UDS_ACCESS
    UDS_MODIFICATION_TIME:int   =  StandardFieldTypes.UDS_MODIFICATION_TIME
    UDS_ACCESS_TIME:int         =  StandardFieldTypes.UDS_ACCESS_TIME         
    UDS_CREATION_TIME:int       =  StandardFieldTypes.UDS_CREATION_TIME       
    UDS_FILE_TYPE:int           =  StandardFieldTypes.UDS_FILE_TYPE           
    UDS_LINK_DEST:int           =  StandardFieldTypes.UDS_LINK_DEST           
    UDS_URL:int                 =  StandardFieldTypes.UDS_URL                 
    UDS_MIME_TYPE:int           =  StandardFieldTypes.UDS_MIME_TYPE           
    UDS_GUESSED_MIME_TYPE:int   =  StandardFieldTypes.UDS_GUESSED_MIME_TYPE   
    UDS_XML_PROPERTIES:int      =  StandardFieldTypes.UDS_XML_PROPERTIES      
    UDS_EXTENDED_ACL:int        =  StandardFieldTypes.UDS_EXTENDED_ACL        
    UDS_ACL_STRING:int          =  StandardFieldTypes.UDS_ACL_STRING          
    UDS_DEFAULT_ACL_STRING:int  =  StandardFieldTypes.UDS_DEFAULT_ACL_STRING  
    UDS_DISPLAY_NAME:int        =  StandardFieldTypes.UDS_DISPLAY_NAME        
    UDS_TARGET_URL:int          =  StandardFieldTypes.UDS_TARGET_URL          
    UDS_DISPLAY_TYPE:int        =  StandardFieldTypes.UDS_DISPLAY_TYPE        
    UDS_ICON_OVERLAY_NAMES:int  =  StandardFieldTypes.UDS_ICON_OVERLAY_NAMES  
    UDS_COMMENT :int            =  StandardFieldTypes.UDS_COMMENT             
    UDS_DEVICE_ID:int           =  StandardFieldTypes.UDS_DEVICE_ID           
    UDS_INODE:int               =  StandardFieldTypes.UDS_INODE               
    UDS_RECURSIVE_SIZE:int      =  StandardFieldTypes.UDS_RECURSIVE_SIZE      
    UDS_LOCAL_USER_ID:int       =  StandardFieldTypes.UDS_LOCAL_USER_ID       
    UDS_LOCAL_GROUP_ID:int      =  StandardFieldTypes.UDS_LOCAL_GROUP_ID      
    UDS_EXTRA:int               =  StandardFieldTypes.UDS_EXTRA               
    UDS_EXTRA_END:int           =  StandardFieldTypes.UDS_EXTRA_END           
    
    Field = Field
    
    # ### END   Fields
    
    def __init__(self, buff:typing.Optional[stat_result] = None, name:str = str()):
        # NOTE: 2025-01-04 16:00:10
        # my guess here is that QT_STATBUF is equivalent to Pyton's stat_result
        # so let's go with that...
        self._d_ = _UDSEntryPrivate_()
        
        if sys.platform.startswith("win32"):
            self._d_.reserve(8)
        else:
            self._d_.reserve(10)
            
        if isinstance(name, str) and len(name):
            self._d_.insert(self.UDS_NAME, name)
        
        if isinstance(buff, stat_result):
            self._d_.insert(self.UDS_SIZE, buff.st_size)
            self._d_.insert(self.UDS_DEVICE_ID, buff.st_dev)
            self._d_.insert(self.UDS_INODE, buff.st_ino)
            self._d_.insert(self.UDS_FILE_TYPE, stat.S_IFMT(buff.st_mode)) # extract file type — does the same thing as C++ line below
            # d->insert(UDS_FILE_TYPE, buff.st_mode & QT_STAT_MASK); // extract file type; see comments at top of utils.py
            self._d_.insert(self.UDS_ACCESS, stat.S_IMODE(buff.st_mode)) # extract permissions — does the same thing as C++ line below
            # NOTE: 2025-01-05 21:31:50 stat.S_IMODE(buff.st_mode) is theoretically the same as buff.st_mode & 0o7777 on a UNIX machine # (NOTE: octal value!!!)
            # self.insert(self.UDS_ACCESS, buff.st_mode & 0o7777) # extract permissions — does the same thing as C++ line below
            # d->insert(UDS_ACCESS, buff.st_mode & 07777); // extract permissions; see comments at top of utils.py
            
            if HAS_STATX and isinstance(buff, statx.stat_result):
                self._d_.insert(self.UDS_MODIFICATION_TIME, buff.st_mtime)
                self._d_.insert(self.UDS_ACCESS_TIME, buff.st_atime)
            else:
                # self.insert(self.UDS_MODIFICATION_TIME, buff.st_mtime_ns) # time in ns as integer
                self._d_.insert(self.UDS_MODIFICATION_TIME, int(buff.st_mtime))
                # self.insert(self.UDS_ACCESS_TIME, buff.st_atime_ns)       # time in ns as integer 
                self._d_.insert(self.UDS_ACCESS_TIME, int(buff.st_atime))
                
            # NOTE: 2025-01-06 14:13:49
            # Incidentally, they don't seem to try & call statx here, in KIO::UDSEntry c'tor
            # hence they don't explore creation time ?!?
            
            if not sys.platform.startswith("win32"):
            #ifndef Q_OS_WIN
                self._d_.insert(self.UDS_LOCAL_USER_ID,  buff.st_uid) # user  ID of the file owner — UNIX only
                self._d_.insert(self.UDS_LOCAL_GROUP_ID, buff.st_gid) # group ID of the file owner — UNIX only
            #endif
        
    def __eq__(self, other) -> bool:
        if type(other) != type(self):
            return False
        
        if self.count() != other.count():
            return False
        
        for field in self.fields():
            if not other.contains(field):
                return False
            
            if field & self.UDS_STRING:
                if self.stringValue(field) != other.stringValue(field):
                    return False
                
            elif fielf & self.UDS_NUMBER:
                if self.numberValue(field) != other.numberValue(field):
                    return False
                
        return True
    
    def reserve(self, size:int): 
        self._d_.reserve(size)
    
    def replace(self, udsField:int, value:typing.Union[str, int]):
        self._d_.replace(udsField, value)
        
    def count(self) -> int:
        return self._d_.count()
    
    def stringValue(self, udsField:int) -> str:
        return self._d_.stringValue(udsField)
    
    def numberValue(self, udsField:int, defaultValue:int = -1) -> int:
        return self._d_.numberValue(udsField, defaultValue)
    
    def fields(self) -> list[int]:
        return self._d_.fields()
    
    def contains(self, udsField:int) -> bool:
        return self._d_.contains(udsField)
    
    def clear(self):
        self._d_.clear()
    
    def fastInsert(self, field:int, value:typing.Union[str, int]):
        self._d_.insert(field, value)
    
    def isDir(self) -> bool:
        return utils.isDirMask(self.numberValue(self.UDS_FILE_TYPE))
    
    def isLink(self) -> bool:
        return len(self.stringValue(self.UDS_LINK_DEST)) > 0
        # or:
        # return utils.isLinkMask(self.numberValue(self.UDS_FILE_TYPE))

    
    
