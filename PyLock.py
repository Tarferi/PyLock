# -*- coding: utf-8 -*-
import os, sys, time;
from datetime import datetime;
from shutil import copyfile
from sys import exit
from ctypes import windll, CDLL, RTLD_GLOBAL, c_int, Structure, c_uint16, c_uint32, c_char, c_short, c_char_p, c_int32, POINTER, c_byte, c_void_p, c_float, c_size_t, GetLastError, create_string_buffer, byref

def is_int(value):
    try:
        int(value)
        return True;
    except Exception:
        return False;

class ReadBuffer:
    
    def __init__(self, **kwargs):
        data = kwargs.pop('data', False) 
        ffile = kwargs.pop('file', False) 
        if ffile is not False:
            f = open(ffile, "rb");
            self.__bytes = [];
            self.__position = 0;
            self.__size = 0;  
            try:
                byte = f.read(1)
                while byte != "":
                    self.__bytes.append(ord(byte));
                    self.__size = self.__size + 1;
                    byte = f.read(1)
            finally:
                f.close()
        if data is not False:
            self.__bytes = data;
            self.__position = 0;
            self.__size = len(self.__bytes);

    def readByte(self):
        byte = self.__bytes[self.__position];
        self.__position = self.__position + 1;
        return byte;
    
    def readShort(self):
        return (self.readByte()) | (self.readByte() << 8);

    def readInt(self):
        return (self.readShort()) | (self.readShort() << 16);

    def readArray(self, size):
        ret = [];
        for _ in range(0, size):
            byte = self.readByte();    
            ret.append(byte);
        return ret;

    def getSize(self):
        return self.__size;

    def readZeroDelimString(self):
        string = "";
        byte = self.readByte();
        while(byte != 0):
            string = string + chr(byte);
            byte = self.readByte();    
        return string;

    def getRestArray(self):
        ret = [];
        while(not self.isDone()):
            ret.append(self.readByte());
        return ret;

    def readFixedString(self, length):
        string = "";
        for _ in range(0, length):
            byte = self.readByte();    
            string = string + chr(byte);
        return string;

    def isDone(self):
        return self.__position == self.__size;

class WriteBuffer:
    
    def __init__(self):
        self.__bytes = [];
        self.__position = 0;
        
    def writeByte(self, byte):
        self.__bytes.append(byte);
        self.__position = self.__position + 1;
        
    def writeShort(self, value):
        self.writeByte((value >> 0) & 0xff);
        self.writeByte((value >> 8) & 0xff);
        
    def writeInt(self, value):
        self.writeShort(int((value >> 0) & 0xffff));
        self.writeShort(int((value >> 16) & 0xffff));
    
    def writeToFile(self, ffile):
        with open(ffile, 'wb') as f2:
            for i in range(0, self.__position):
                byte = self.__bytes[i];
                try:
                    f2.write(chr(byte));
                except Exception:
                    pass;
    
    def writeFixedLengthString(self, string):
        for char in string:
            self.writeByte(ord(char));
    
    def writeZeroDelimString(self, string):
        for char in string:
            self.writeByte(ord(char));
        self.writeByte(0);

    def writeArray(self, array):
        for byte in array:
            self.writeByte(byte);

    def getRestArray(self):
        return self.__bytes;

class PyChkSection:

    @staticmethod
    def str2Class(className):
        try:
            return getattr(sys.modules[__name__], className)
        except AttributeError:
            return False;

    def __init__(self, name, size, data):
        self.name = name;
        self.size = size;
        self.__data = data;
        self._parse(ReadBuffer(data=data));

    def write(self, buf):
        dataBuffer = WriteBuffer();
        self._write(dataBuffer);
        dataBuffer = dataBuffer.getRestArray();
        buf.writeFixedLengthString(self.name);
        buf.writeInt(len(dataBuffer));
        buf.writeArray(dataBuffer);
    
    def _parse(self, _):
        pass
        
    def _write(self, buf):
        buf.writeArray(self.__data);
    
    @staticmethod
    def parse(name, size, data):
        cls = PyChkSection.str2Class("PyChkSection_" + name.replace(" ", "_"));
        if not cls:
            return PyChkSection(name, size, data);
        else:
            return cls(name, size, data);

class PyChk:

    def __parseSections(self):
        while(not self.__buffer.isDone()):
            name = self.__buffer.readFixedString(4);
            size = self.__buffer.readInt();
            section = PyChkSection.parse(name, size, self.__buffer.readArray(size));
            self.sections.append(section);
        pass

    def __init__(self, data):
        self.__buffer = ReadBuffer(data=data);
        self.sections = [];
        self.__parseSections();

    def getSection(self, name):
        for section in self.sections:
            if section.name == name:
                return section;
        print("Section \"" + name + "\"not found")
        exit(1);
    
    def setSection(self, section):
        if section is not False:
            for i in range(0, len(self.sections)):
                if self.sections[i].name == section.name:
                    self.sections[i] = section;
                    return;
            self.sections.append(section);
    
    def writeToBuffer(self):
        sbuffer = WriteBuffer();
        for section in self.sections:
            section.write(sbuffer);
        cbuffer = [];
        for byte in sbuffer.getRestArray():
            cbuffer.append(chr(byte));
        return cbuffer;
            
    def writeToFile(self, ffile):
        sbuffer = WriteBuffer();
        for section in self.sections:
            section.write(sbuffer);
        sbuffer.writeToFile(ffile);

class PyChkSection_STR_(PyChkSection):
    
    def getRawString(self, index):
        string = "";
        off = 2 + (2 * self.original_strings);
        offset = self.offsets[index - 1] - off;
        for i in range(offset, len(self.originalData)):
            char = self.originalData[i];
            if char == 0:
                break;
            else:
                string = string + chr(char);
        if(len(string) > 0):
            pass
        return string;
    
    def setRawString(self, index, string):
        off = 2 + (2 * self.original_strings);
        offset = self.offsets[index - 1] - off;
        for i in range(0, len(string)):
            self.originalData[offset + i] = ord(string[i]);
        self.originalData[offset + len(string)] = 0;
        pass

    def _parse(self, buf):
        self.offsets = [];
        self.original_strings = buf.readShort();
        for _ in range(0, self.original_strings):
            offset = buf.readShort();
            self.offsets.append(offset);
        self.originalData = buf.getRestArray();

    def getNewStringIndex(self, string):
        
        # Shift current offsets
        for i in range(0, len(self.offsets)):
            self.offsets[i] = self.offsets[i] + 2;
        offset = 4 + (2 * len(self.offsets)) + len(self.originalData);
        if(offset + (len(string) + 1) > 0xffff):
            print("Failed to insert new string");
            exit(1);  
        self.offsets.append(offset);
        for char in string:
            self.originalData.append(ord(char));
        self.originalData.append(0);
        return len(self.offsets);
    
    def deleteStringIndex(self, index):
        index = index - 1;
        for i in range(index, len(self.offsets)):
            self.offsets[i] = self.offsets[i] - 2;
        self.offsets.pop(index);

    def _write(self, buf):
        buf.writeShort(len(self.offsets));
        for offset in self.offsets:
            buf.writeShort(offset);
        buf.writeArray(self.originalData);

class PyChkSection_TRIG(PyChkSection):
    
    class PyChkCondition:
        
        def __init__(self, buf=None):
            if not buf is None:
                self.locationNumber = buf.readInt();
                self.groupNumber = buf.readInt();
                self.Quantifier = buf.readInt();
                self.UnitID = buf.readShort();
                self.Comparision = buf.readByte();
                self.Condition = buf.readByte();
                self.Resource = buf.readByte();
                self.Flags = buf.readByte();
                self.Unused = buf.readShort();
            
        def write(self, buf):
            buf.writeInt(self.locationNumber);
            buf.writeInt(self.groupNumber);
            buf.writeInt(self.Quantifier);
            buf.writeShort(self.UnitID);
            buf.writeByte(self.Comparision);
            buf.writeByte(self.Condition);
            buf.writeByte(self.Resource);
            buf.writeByte(self.Flags);
            buf.writeShort(self.Unused);
    
    class PyChkAction:
        
        def __init__(self, buf=None):
            if not buf is None:
                self.SourceLocation = buf.readInt();
                self.TriggerText = buf.readInt();
                self.WAVStringNumber = buf.readInt();
                self.Time = buf.readInt();
                self.Player = buf.readInt();
                self.Group = buf.readInt();
                
                self.UnitType = buf.readShort();
                
                self.ActionType = buf.readByte();
                self.UnitsNumber = buf.readByte();
                self.Flags = buf.readByte();
                
                self.Unused = buf.readArray(3);
            
        def write(self, buf):
            buf.writeInt(self.SourceLocation);
            buf.writeInt(self.TriggerText if is_int(self.TriggerText) else self.TriggerText.index);
            buf.writeInt(self.WAVStringNumber if is_int(self.WAVStringNumber) else self.WAVStringNumber.index);
            buf.writeInt(self.Time);
            buf.writeInt(self.Player);
            buf.writeInt(self.Group);

            buf.writeShort(self.UnitType);
                    
            buf.writeByte(self.ActionType);
            buf.writeByte(self.UnitsNumber);
            buf.writeByte(self.Flags);
            
            buf.writeArray(self.Unused);
            
    def _parse(self, buf):
        self.conditions = [];
        self.actions = [];
        self.flags = [];
        self.players = [];
        
        while not buf.isDone():
            cond = [];
            for _ in range (0, 16):
                cond.append(PyChkSection_TRIG.PyChkCondition(buf));
            self.conditions.append(cond);
            
            act = [];
            for _ in range (0, 64):
                act.append(PyChkSection_TRIG.PyChkAction(buf));
            self.actions.append(act);
            
            self.flags.append(buf.readInt());
            
            players = buf.readArray(28);
            self.players.append(players);
            
    def _write(self, buf):
        for i in range(0, len(self.conditions)):
            for condition in self.conditions[i]:
                condition.write(buf);
         
            for action in self.actions[i]:
                action.write(buf);
                
            buf.writeInt(self.flags[i]);
           
            buf.writeArray(self.players[i]);
            
class PyChkSection_SPRP(PyChkSection):
    
    def _parse(self, buf):
        self.str_scenarioName = buf.readShort();
        self.str_scenarioDescription = buf.readShort();
            
    def _write(self, buf):
        buf.writeShort(self.str_scenarioName if is_int(self.str_scenarioName) else self.str_scenarioName.index);
        buf.writeShort(self.str_scenarioDescription if is_int(self.str_scenarioDescription) else self.str_scenarioDescription.index);

def extractFile(theMapFile, theFile):
    h = MpqOpenArchiveForUpdateEx(theMapFile, MOAU_OPEN_EXISTING | MOAU_READ_ONLY)
    if SFInvalidHandle(h):
        print("Invalid file");
        exit(1);
    files = []
    totalsize = 0
    
    if hasattr(sys, 'frozen'):
        BASE_DIR = os.path.dirname(unicode(sys.executable, sys.getfilesystemencoding()))
    else:
        BASE_DIR = os.path.dirname(os.path.dirname(unicode(__file__, sys.getfilesystemencoding())))
    
    # for e in SFileListFiles(h, ""):
    for e in SFileListFiles(h, str('\r\n'.join([os.path.join(BASE_DIR, 'Libs', 'Data', 'Listfile.txt')]))):
        if e.fileExists:
            files.append(e)
            totalsize += e.fullSize
    for e in files:
        n = e.fileName;
        if n == theFile:
            pass
            fh = SFileOpenFileEx(h, n)
            if fh:
                r = SFileReadFile(fh)
                SFileCloseFile(fh)
                MpqCloseUpdatedArchive(h)
                return r[0];
            else:
                print("Failed to extract file");
                exit(1);
    
    MpqCloseUpdatedArchive(h)
    return False;
 
def createFile(theMapFile, theFile, vbuffer):
    maxFiles = 1024;
    blocksize = 3;
    h = MpqOpenArchiveForUpdateEx(theMapFile, MOAU_CREATE_ALWAYS, maxFiles, blocksize);
    if SFInvalidHandle(h):
        print("Failed to create new file");
        exit(1);
    MpqCloseUpdatedArchive(h);
    h = MpqOpenArchiveForUpdate(theMapFile, MOAU_OPEN_EXISTING | MOAU_MAINTAIN_LISTFILE)
    if SFInvalidHandle(h):
        print("Failed to create new file");
        exit(1);
    
    vbuffer = "".join(vbuffer);
    MpqAddFileFromBuffer(h, vbuffer, theFile);
    MpqCloseUpdatedArchive(h);
 
def addPad(string, number):
    prePad = "";
    for _ in range(0, number):
        prePad = prePad + "0";
    string = str(prePad) + str(string);
    return string[len(string) - number:];

def replaceTime(string, suffix, dt):
    dt = datetime.fromtimestamp(dt);
    M = dt.month;
    D = dt.day;
    Y = dt.year;
    H = dt.hour;
    m = dt.minute;
    S = dt.second;
    for dataStr, dateVal in [["DD", D], ["MM", M], ["YYYY", Y], ["HH", H], ["mm", m], ["SS", S]]:
        dateVal = addPad(dateVal, len(dataStr));
        dataStr = dataStr + suffix;
        string = string.replace(dataStr, dateVal);
    return string;

def getNewCondition():
    condition = PyChkSection_TRIG.PyChkCondition();
    condition.locationNumber = 0;
    condition.groupNumber = 0;
    condition.Quantifier = 0;
    condition.UnitID = 0;
    condition.Comparision = 0;
    condition.Condition = 0;
    condition.Resource = 0;
    condition.Flags = 0;
    condition.Unused = 0;
    return condition;

def getNewAction():
    action = PyChkSection_TRIG.PyChkAction();
    action.SourceLocation = 0;
    action.TriggerText = 0;
    action.WAVStringNumber = 0;
    action.Time = 0;
    action.Player = 0;
    action.Group = 0;
    action.UnitType = 0;
    action.ActionType = 0;
    action.UnitsNumber = 0;
    action.Flags = 0;
    action.Unused = [0, 0, 0];
    return action;
 
def getNewConditionsArray():
    cond = [];
    for _ in range(0, 16):
        cond.append(getNewCondition());
    return cond;

def getNewActionsArray():
    act = [];
    for _ in range(0, 64):
        act.append(getNewAction());
    return act;

def addTrigger(v3TRIG, comparator, stringIndex, maxAllowedTime):
    conds = getNewConditionsArray();
    acts = getNewActionsArray();
    flag = 0;
    players = [];
    for _ in range(0, 28):
        players.append(0);
    players[17] = 1;
    conds[0].groupNumber = 334581;
    conds[0].Comparision = comparator;
    conds[0].Condition = 15;  # Deaths
    conds[0].Quantifier = maxAllowedTime;
    
    acts[0].ActionType = 9;  # Display text
    acts[0].Flags = 4;
    acts[0].TriggerText = stringIndex;

    acts[1].ActionType = 4;  # Wait
    acts[1].Time = 5000;
    
    acts[2].ActionType = 2;  # Defeat
    
    v3TRIG.conditions.append(conds);
    v3TRIG.actions.append(acts);
    v3TRIG.flags.append(flag);
    v3TRIG.players.append(players);
    
    pass

def getNewTimeString(userString, timeFrom, timeTo):
    userString = replaceTime(userString, "F", timeFrom);
    userString = replaceTime(userString, "T", timeTo);
    return userString;

def getNonZeroMembers(array, func):
    nz = 0;
    for member in array:
        if func(member) != 0:
            nz = nz + 1;
    return nz;

def getNthNonZeroMember(array, index, func):
    nz = 0;
    for member in array:
        if func(member) != 0:
            if nz == index:
                return member;
            nz = nz + 1;
    return None;

def isOurTrigger(v3TRIG, index):
    conditions = v3TRIG.conditions[index];
    players = v3TRIG.players[index];
    flag = v3TRIG.flags[index];
    actions = v3TRIG.actions[index];
    condI = lambda x : x.Condition;
    actI = lambda x: x.ActionType;
    if flag == 0 and getNonZeroMembers(conditions, condI) == 1 and getNonZeroMembers(actions, actI) == 3 and getNonZeroMembers(players, lambda x : x) == 1 and players[17] == 1:
        cond = getNthNonZeroMember(conditions, 0, condI);
        if cond.groupNumber == 334581 and cond.Condition == 15:
            actDisplayText = getNthNonZeroMember(actions, 0, actI);
            if actDisplayText.ActionType == 9 and actDisplayText.Flags == 4:
                actWait = getNthNonZeroMember(actions, 1, actI);
                if actWait.ActionType == 4:
                    actDefeat = getNthNonZeroMember(actions, 2, actI);
                    if actDefeat.ActionType == 2:
                        return True;
    return False;

def patchFile(inputFile, outputFile, userString, minusYears, minusDays, minusHours, minusMinutes, minusSeconds, plusYears, plusDays, plusHours, plusMinutes, plusSeconds):
    AT_LEAST = 0;
    AT_MOST = 1;
    
    # Calculate values
    now = int(time.time());
    second = 1;
    minute = 60 * second;
    hour = 60 * minute;
    day = 24 * hour;
    year = 256 * day;
    minuses = [minusYears * year, minusDays * day, minusHours * hour, minusMinutes * minute, minusSeconds * second];
    pluses = [plusYears * year, plusDays * day, plusHours * hour, plusMinutes * minute, plusSeconds * second];
    totalMinus = 0;
    totalPlus = 0;
    for minus in minuses:
        totalMinus = totalMinus + minus;
    for plus in pluses:
        totalPlus = totalPlus + plus;
    lockFrom = now + totalMinus;
    lockTo = now + totalPlus;
    
    # Deal with time lock trigger
    chkFile = "staredit\scenario.chk";
    chkStrData = extractFile(inputFile, chkFile);
    if chkStrData is False:
        print("Failed to open the file");
        exit(1);
    chkData = [];
    for char in chkStrData:
        chkData.append(ord(char)); 
    
    v3 = PyChk(chkData);
    v3TRIG = v3.getSection("TRIG");
    v3STR = v3.getSection("STR ");

    # Check if there are already our triggers 
    toDel = [];
    for triggerIndex in range(0, len(v3TRIG.actions)):
        if isOurTrigger(v3TRIG, triggerIndex):
            toDel.append(triggerIndex);
    toDel.sort(reverse=True) 
    if len(toDel) != 0:
        stringIndexToRemove = v3TRIG.actions[toDel[0]][3].TriggerText;
        v3STR.deleteStringIndex(stringIndexToRemove);
        print("Removing previously inserted triggers. Please repair STR section soon!");
    for toDelIndex in toDel:
        v3TRIG.conditions.pop(toDelIndex);
        v3TRIG.actions.pop(toDelIndex);
        v3TRIG.flags.pop(toDelIndex);
        v3TRIG.players.pop(toDelIndex);
    
    # Add trigger
    string = v3STR.getNewStringIndex(getNewTimeString(userString, lockFrom, lockTo));
    addTrigger(v3TRIG, AT_LEAST, string, lockTo);
    addTrigger(v3TRIG, AT_MOST, string, lockFrom);
    
    # Save to file
    vbuffer = v3.writeToBuffer();
    if inputFile != outputFile:
        try:
            os.remove(outputFile)
        except:
            pass
        copyfile(inputFile, outputFile);

    createFile(outputFile, chkFile, vbuffer);
    print("Done");

def transformUserString(string):
    for i in range(0, 32):
        r1 = hex(i)[2:];
        r2 = "0" + r1
        r2 = r2[len(r2)-2:]; 
        repl1 = "<" + r1 + ">";
        repl2 = "<" + r2 + ">";
        string = string.replace(repl1, chr(i));
        string = string.replace(repl2, chr(i));
    return string;

def work():
    
    skip = False;
    inputFile = None;
    outputFile = None;
    userString = None;
    fromString = None;
    toString = None;
    showHelp = True;
    args = len(sys.argv);
    for argI in range(0, args):
        if skip:
            skip = False;
            continue;
        arg = sys.argv[argI];
        if arg == "-i" or arg == "--input":
            if inputFile is not None or argI + 1 == args:
                print("Invalid option for input file");
                exit(2);
            inputFile = sys.argv[argI + 1];
            skip = True;
            showHelp = False;
        elif arg == "-o" or arg == "--output":
            if outputFile is not None or argI + 1 == args:
                print("Invalid option for output file");
                exit(2);
            outputFile = sys.argv[argI + 1];
            skip = True;
            showHelp = False;
        elif arg == "-f" or arg == "--from":
            if fromString is not None or argI + 1 == args:
                print("Invalid option for from date");
                exit(2);
            fromString = sys.argv[argI + 1];
            skip = True;
            showHelp = False;
        elif arg == "-t" or arg == "--to":
            if toString is not None or argI + 1 == args:
                print("Invalid option for to date");
                exit(2);
            toString = sys.argv[argI + 1];
            skip = True;
            showHelp = False;
        elif arg == "-m" or arg == "--message":
            if userString is not None or argI + 1 == args:
                print("Invalid option for message");
                exit(2);
            userString = transformUserString(sys.argv[argI + 1]);
            skip = True;
            showHelp = False;
        elif arg == "-h" or arg == "--help":
            showHelp = True;
            break;
            
    if showHelp:
        print("Starcraft Map Time locker by iThief");
        print("\r\n\r\nUsage:\r\n");
        print("\t-i <input_file>      Input map file\r\n");
        print("\t-o <output_file>     Output map file (can be the same as output)\r\n");
        print("\t-f <unlock_begin>    Relative specification of unlock begin (see below)\r\n");
        print("\t-t <unlock_begin>    Relative specification of unlock begin (see below)\r\n");
        print("\t-m <message>         Message to display when map is locked (see below)\r\n");
        print("\r\n\r\nDate format:\r\n");
        print("\t<Years>:<Days>:<Hours>:<Minutes>:<Seconds>\r\n");
        print("\r\n\r\nDate Example:\r\n");
        print("\t\"0:-1:0:0:0     Means yesterday at this time\"\r\n");
        print("\r\n\r\nMessage format:\r\n");
        print("\t\"This uses Scmdraft string format (See Scmdraft string editor)\"\r\n");
        print("\t\"Message can include variables YYYY[F|T], MM[F|T], DD[F|T], HH[F|T], mm[F|T], SS[F|T]   where F means From and T means To\"\r\n");
        print("\r\n\r\nExample:\r\n");
        print("\tlock.exe -i my_cool_map.scx -o my_cool_map_locked.scx -f 0:-1:0:0:0 -t 0:1:0:0:0 -m \"Yo I made this map time-locked. It will be unplayable on MMT.DDT at mmT:ssT.\"\r\n");
        print("\r\nAbove example command will product my_cool_map_locked.scx that will be only playable for a day (timezones might vary). When it's no longer playable, it will display a message telling people until when it was playable, give them 5 seconds to read it and then defeat for all players.\r\n");
        print("\r\nIt's not recommended to use it in loop without repairing STR section (editing in editor or something).\r\n");
        exit(3);
        
    MpqInitialize();
    p = [];
    for string in [fromString, toString]:
        strings = string.split(":");
        if len(strings) != 5:
            print("Invalid date string");
            exit(1);
        d = [];
        for i in strings:
            if not is_int(i):
                print("Invalid date string");
                exit(1);
            d.append(int(i));
        p.append(d);

    minusYears, minusDays, minusHours, minusMinutes, minusSeconds = p[0];
    plusYears, plusDays, plusHours, plusMinutes, plusSeconds = p[1];
    
    patchFile(inputFile, outputFile, userString, minusYears, minusDays, minusHours, minusMinutes, minusSeconds, plusYears, plusDays, plusHours, plusMinutes, plusSeconds);

cwd = os.getcwd()
if hasattr(sys, 'frozen'):
    SFmpq_DIR = os.path.join(os.path.dirname(unicode(sys.executable, sys.getfilesystemencoding())), 'Libs')
else:
    SFmpq_DIR = os.path.dirname(unicode(__file__, sys.getfilesystemencoding()))
if SFmpq_DIR:
    try:
        os.chdir(SFmpq_DIR)
    except Exception:
        cwd = False;
FOLDER = False
_SFmpq = False;
try:
    _SFmpq = windll.SFmpq
except:
    try:
        _SFmpq = windll.SFmpq64
    except:
        try:
            _SFmpq = CDLL("SFmpq.dylib", RTLD_GLOBAL)
        except:
            FOLDER = True
if cwd is not False:
    os.chdir(cwd)
if _SFmpq is False:
    print("Failed to load MPQ libraries.");
    exit(1);

class SFile:

    def __init__(self, text='', ffile='<Internal SFile>'):
        self.text = text
        self.file = ffile

    def write(self, text):
        self.text += text

    def read(self):
        return self.text

    def close(self):
        pass

    def __str__(self):
        return self.file

MPQ_ERROR_MPQ_INVALID = 0x85200065
MPQ_ERROR_FILE_NOT_FOUND = 0x85200066
MPQ_ERROR_DISK_FULL = 0x85200068  # Physical write file to MPQ failed
MPQ_ERROR_HASH_TABLE_FULL = 0x85200069
MPQ_ERROR_ALREADY_EXISTS = 0x8520006A
MPQ_ERROR_BAD_OPEN_MODE = 0x8520006C  # When MOAU_READ_ONLY is used without MOAU_OPEN_EXISTING

MPQ_ERROR_COMPACT_ERROR = 0x85300001

# MpqOpenArchiveForUpdate flags
MOAU_CREATE_NEW = 0x00  # If archive does not exist, it will be created. If it exists, the function will fail
MOAU_CREATE_ALWAYS = 0x08  # Will always create a new archive
MOAU_OPEN_EXISTING = 0x04  # If archive exists, it will be opened. If it does not exist, the function will fail
MOAU_OPEN_ALWAYS = 0x20  # If archive exists, it will be opened. If it does not exist, it will be created
MOAU_READ_ONLY = 0x10  # Must be used with MOAU_OPEN_EXISTING. Archive will be opened without write access
MOAU_MAINTAIN_ATTRIBUTES = 0x02  # Will be used in a future version to create the (attributes) file
MOAU_MAINTAIN_LISTFILE = 0x01  # Creates and maintains a list of files in archive when they are added, replaced, or deleted

# MpqOpenArchiveForUpdateEx constants
DEFAULT_BLOCK_SIZE = 3  # 512 << number = block size
USE_DEFAULT_BLOCK_SIZE = 0xFFFFFFFF  # Use default block size that is defined internally

# MpqAddFileToArchive flags
MAFA_EXISTS = 0x80000000  # This flag will be added if not present
MAFA_UNKNOWN40000000 = 0x40000000  # Unknown flag
MAFA_MODCRYPTKEY = 0x00020000  # Used with MAFA_ENCRYPT. Uses an encryption key based on file position and size
MAFA_ENCRYPT = 0x00010000  # Encrypts the file. The file is still accessible when using this, so the use of this has depreciated
MAFA_COMPRESS = 0x00000200  # File is to be compressed when added. This is used for most of the compression methods
MAFA_COMPRESS2 = 0x00000100  # File is compressed with standard compression only (was used in Diablo 1)
MAFA_REPLACE_EXISTING = 0x00000001  # If file already exists, it will be replaced

# MpqAddFileToArchiveEx compression flags
MAFA_COMPRESS_STANDARD = 0x08  # Standard PKWare DCL compression
MAFA_COMPRESS_DEFLATE = 0x02  # ZLib's deflate compression
MAFA_COMPRESS_WAVE = 0x81  # Standard wave compression
MAFA_COMPRESS_WAVE2 = 0x41  # Unused wave compression

# Flags for individual compression types used for wave compression
MAFA_COMPRESS_WAVECOMP1 = 0x80  # Main compressor for standard wave compression
MAFA_COMPRESS_WAVECOMP2 = 0x40  # Main compressor for unused wave compression
MAFA_COMPRESS_WAVECOMP3 = 0x01  # Secondary compressor for wave compression

# ZLib deflate compression level constants (used with MpqAddFileToArchiveEx and MpqAddFileFromBufferEx)
Z_NO_COMPRESSION = 0
Z_BEST_SPEED = 1
Z_BEST_COMPRESSION = 9
Z_DEFAULT_COMPRESSION = -1  # Default level is 6 with current ZLib version

# MpqAddWaveToArchive quality flags
MAWA_QUALITY_HIGH = 1  # Higher compression, lower quality
MAWA_QUALITY_MEDIUM = 0  # Medium compression, medium quality
MAWA_QUALITY_LOW = 2  # Lower compression, higher quality

# SFileGetFileInfo flags
SFILE_INFO_BLOCK_SIZE = 0x01  # Block size in MPQ
SFILE_INFO_HASH_TABLE_SIZE = 0x02  # Hash table size in MPQ
SFILE_INFO_NUM_FILES = 0x03  # Number of files in MPQ
SFILE_INFO_TYPE = 0x04  # Is MPQHANDLE a file or an MPQ?
SFILE_INFO_SIZE = 0x05  # Size of MPQ or uncompressed file
SFILE_INFO_COMPRESSED_SIZE = 0x06  # Size of compressed file
SFILE_INFO_FLAGS = 0x07  # File flags (compressed, etc.), file attributes if a file not in an archive
SFILE_INFO_PARENT = 0x08  # Handle of MPQ that file is in
SFILE_INFO_POSITION = 0x09  # Position of file pointer in files
SFILE_INFO_LOCALEID = 0x0A  # Locale ID of file in MPQ
SFILE_INFO_PRIORITY = 0x0B  # Priority of open MPQ
SFILE_INFO_HASH_INDEX = 0x0C  # Hash table index of file in MPQ
SFILE_INFO_BLOCK_INDEX = 0x0D  # Block table index of file in MPQ

# Return values of SFileGetFileInfo when SFILE_INFO_TYPE flag is used
SFILE_TYPE_MPQ = 0x01
SFILE_TYPE_FILE = 0x02

# SFileListFiles flags
SFILE_LIST_MEMORY_LIST = 0x01  # Specifies that lpFilelists is a file list from memory, rather than being a list of file lists
SFILE_LIST_ONLY_KNOWN = 0x02  # Only list files that the function finds a name for
SFILE_LIST_ONLY_UNKNOWN = 0x04  # Only list files that the function does not find a name for

# SFileOpenArchive flags
SFILE_OPEN_HARD_DISK_FILE = 0x0000  # Open archive without regard to the drive type it resides on
SFILE_OPEN_CD_ROM_FILE = 0x0001  # Open the archive only if it is on a CD-ROM
SFILE_OPEN_ALLOW_WRITE = 0x8000  # Open file with write access

# SFileOpenFileEx search scopes
SFILE_SEARCH_CURRENT_ONLY = 0x00  # Used with SFileOpenFileEx; only the archive with the handle specified will be searched for the file
SFILE_SEARCH_ALL_OPEN = 0x01  # SFileOpenFileEx will look through all open archives for the file. This flag also allows files outside the archive to be used

class SFMPQVERSION(Structure):
    _fields_ = [
        ('Major', c_uint16),
        ('Minor', c_uint16),
        ('Revision', c_uint16),
        ('Subrevision', c_uint16)
    ]

class FILELISTENTRY(Structure):
    _fields_ = [
        ('fileExists', c_uint32),
        ('locale', c_uint32),
        ('compressedSize', c_uint32),
        ('fullSize', c_uint32),
        ('flags', c_uint32),
        ('fileName', c_char * 260)
    ]

    def __getitem__(self, k):
        if self.fullSize:
            p = self.compressedSize / float(self.fullSize)
        else:
            p = 0
        return [self.fileExists, self.locale, self.compressedSize, p, self.fullSize, self.flags, self.fileName][k]

    def __str__(self):
        if self.fullSize:
            p = self.compressedSize / float(self.fullSize)
        else:
            p = 0
        return str([self.fileExists, self.locale, self.compressedSize, p, self.fullSize, self.flags, self.fileName])

class MPQHEADER(Structure):
    _fields_ = [
        ('mpqId', c_int),
        ('headerSize', c_int),
        ('mpqSize', c_int),
        ('unused', c_short),
        ('blockSize', c_short),
        ('hashTableOffset', c_int),
        ('blockTableOffset', c_int),
        ('hashTableSize', c_int),
        ('blockTableSize', c_int),
    ]

class BLOCKTABLEENTRY(Structure):
    _fields_ = [
        ('fileOffset', c_int),
        ('compressedSize', c_int),
        ('fullSize', c_int),
        ('flags', c_int),
    ]

class HASHTABLEENTRY(Structure):
    _fields_ = [
        ('nameHashA', c_int),
        ('nameHashB', c_int),
        ('locale', c_int),
        ('blockTableIndex', c_int),
    ]

class MPQFILE(Structure):
    pass

class MPQARCHIVE(Structure):
    pass

MPQFILE._fields_ = [
    ('nextFile', POINTER(MPQFILE)),
    ('prevFile', POINTER(MPQFILE)),
    ('fileName', c_char * 260),
    ('file', c_int),
    ('parentArc', POINTER(MPQARCHIVE)),
    ('blockEntry', POINTER(BLOCKTABLEENTRY)),
    ('cryptKey', c_int),
    ('filePointer', c_int),
    ('unknown', c_int),
    ('blockCount', c_int),
    ('blockOffsets', POINTER(c_int)),
    ('readStarted', c_int),
    ('streaming', c_byte),
    ('lastReadBlock', POINTER(c_byte)),
    ('bytesRead', c_int),
    ('bufferSize', c_int),
    ('refCount', c_int),
    ('hashEntry', POINTER(HASHTABLEENTRY)),
    ('fileName', c_char_p),
]
MPQARCHIVE._fields_ = [
    ('nextArc', POINTER(MPQARCHIVE)),
    ('prevArc', POINTER(MPQARCHIVE)),
    ('fileName', c_char * 260),
    ('hFile', c_int),
    ('flags', c_int),
    ('priority', c_int),
    ('lastReadFile', POINTER(MPQFILE)),
    ('bufferSize', c_int),
    ('mpqStart', c_int),
    ('mpqEnd', c_int),
    ('mpqHeader', POINTER(MPQHEADER)),
    ('blockTable', POINTER(BLOCKTABLEENTRY)),
    ('hashTable', POINTER(HASHTABLEENTRY)),
    ('readOffset', c_int),
    ('refCount', c_int),
    ('sfMpqHeader', MPQHEADER),
    ('sfFlags', c_int),
    ('sfFileName', c_char_p),
    ('sfExtraFlags', c_int),
]

class MPQHANDLE(c_void_p):

    def __repr__(self):
        return '<MPQHANDLE object at %s: %s>' % (hex(id(self)), hex(self.value))

def MpqInitialize():
    if not FOLDER:
        try:
            _SFmpq.GetLastError.restype = c_int32
        except:
            _SFmpq.GetLastError = None

        _SFmpq.MpqGetVersionString.restype = c_char_p
        _SFmpq.MpqGetVersion.restype = c_float
        _SFmpq.SFMpqGetVersionString.restype = c_char_p
        # _SFmpq.SFMpqGetVersionString2.argtypes = [c_char_p,c_int]
        _SFmpq.SFMpqGetVersion.restype = SFMPQVERSION
        
        _SFmpq.SFileOpenArchive.argtypes = [c_char_p, c_int32, c_uint32, POINTER(MPQHANDLE)]
        _SFmpq.SFileCloseArchive.argtypes = [MPQHANDLE]
        # _SFmpq.SFileOpenFileAsArchive.argtypes = [MPQHANDLE,c_char_p,c_int32,c_int32,POINTER(MPQHANDLE)]
        # _SFmpq.SFileGetArchiveName.argtypes = [MPQHANDLE,c_char_p,c_int32]
        _SFmpq.SFileOpenFile.argtypes = [c_char_p, POINTER(MPQHANDLE)]
        _SFmpq.SFileOpenFileEx.argtypes = [MPQHANDLE, c_char_p, c_uint32, POINTER(MPQHANDLE)]
        _SFmpq.SFileCloseFile.argtypes = [MPQHANDLE]
        _SFmpq.SFileGetFileSize.argtypes = [MPQHANDLE, POINTER(c_uint32)]
        _SFmpq.SFileGetFileSize.restype = c_uint32
        _SFmpq.SFileGetFileArchive.argtypes = [MPQHANDLE, POINTER(MPQHANDLE)]
        # _SFmpq.SFileGetFileName.argtypes = [MPQHANDLE,c_char_p,c_uint32]
        _SFmpq.SFileSetFilePointer.argtypes = [MPQHANDLE, c_int32, POINTER(c_int32), c_uint32]
        _SFmpq.SFileReadFile.argtypes = [MPQHANDLE, c_void_p, c_uint32, POINTER(c_uint32), c_void_p]
        _SFmpq.SFileSetLocale.argtypes = [c_uint32]
        _SFmpq.SFileSetLocale.restype = c_uint32
        _SFmpq.SFileGetBasePath.argtypes = [c_char_p, c_uint32]
        _SFmpq.SFileSetBasePath.argtypes = [c_char_p]

        _SFmpq.SFileGetFileInfo.argtypes = [MPQHANDLE, c_uint32]
        _SFmpq.SFileGetFileInfo.restype = c_size_t
        _SFmpq.SFileSetArchivePriority.argtypes = [MPQHANDLE, c_uint32]
        _SFmpq.SFileFindMpqHeader.argtypes = [c_void_p]
        _SFmpq.SFileFindMpqHeader.restype = c_uint32
        _SFmpq.SFileListFiles.argtypes = [MPQHANDLE, c_char_p, POINTER(FILELISTENTRY), c_uint32]

        _SFmpq.MpqOpenArchiveForUpdate.argtypes = [c_char_p, c_uint32, c_uint32]
        _SFmpq.MpqOpenArchiveForUpdate.restype = MPQHANDLE
        _SFmpq.MpqCloseUpdatedArchive.argtypes = [MPQHANDLE, c_uint32]
        _SFmpq.MpqCloseUpdatedArchive.restype = c_uint32
        _SFmpq.MpqAddFileToArchive.argtypes = [MPQHANDLE, c_char_p, c_char_p, c_uint32]
        _SFmpq.MpqAddWaveToArchive.argtypes = [MPQHANDLE, c_char_p, c_char_p, c_uint32, c_uint32]
        _SFmpq.MpqRenameFile.argtypes = [MPQHANDLE, c_char_p, c_char_p]
        _SFmpq.MpqDeleteFile.argtypes = [MPQHANDLE, c_char_p, c_char_p]
        _SFmpq.MpqCompactArchive.argtypes = [MPQHANDLE]

        _SFmpq.MpqOpenArchiveForUpdateEx.argtypes = [c_char_p, c_uint32, c_uint32, c_uint32]
        _SFmpq.MpqOpenArchiveForUpdateEx.restype = MPQHANDLE
        _SFmpq.MpqAddFileToArchiveEx.argtypes = [MPQHANDLE, c_char_p, c_char_p, c_uint32, c_uint32, c_uint32]
        _SFmpq.MpqAddFileFromBufferEx.argtypes = [MPQHANDLE, c_void_p, c_uint32, c_char_p, c_uint32, c_uint32]
        _SFmpq.MpqAddFileFromBuffer.argtypes = [MPQHANDLE, c_void_p, c_uint32, c_char_p, c_uint32]
        _SFmpq.MpqAddWaveFromBuffer.argtypes = [MPQHANDLE, c_void_p, c_uint32, c_char_p, c_uint32, c_uint32]
        _SFmpq.MpqRenameAndSetFileLocale.argtypes = [MPQHANDLE, c_char_p, c_char_p, c_int, c_int]
        _SFmpq.MpqDeleteFileWithLocale.argtypes = [MPQHANDLE, c_char_p, c_uint32]
        _SFmpq.MpqSetFileLocale.argtypes = [MPQHANDLE, c_char_p, c_uint32, c_uint32]

DEBUG = False

def debug_log(func):
    if DEBUG:

        def do_log(*args, **kwargs):
            result = func(*args, **kwargs)
            print "Func  : %s" % func.__name__
            print "Args  : %s" % (args,)
            print "kwargs: %s" % kwargs
            print "Result: %s" % (result,)
            return result

        return do_log
    else:
        return func

@debug_log
def SFGetLastError():
    # SFmpq only implements its own GetLastError on platforms other than windows
    if _SFmpq.GetLastError == None:
        return GetLastError()
    return _SFmpq.GetLastError()

@debug_log
def SFInvalidHandle(h):
    return not isinstance(h, MPQHANDLE) or h.value in [None, 0, -1]

@debug_log
def MpqGetVersionString():
    return _SFmpq.MpqGetVersionString()

@debug_log
def MpqGetVersion():
    return _SFmpq.MpqGetVersion()

@debug_log
def SFMpqGetVersionString():
    return _SFmpq.SFMpqGetVersionString()

@debug_log
def SFMpqGetVersion():
    return _SFmpq.SFMpqGetVersion()

@debug_log
def SFileOpenArchive(path, priority=0, flags=SFILE_OPEN_HARD_DISK_FILE):
    f = MPQHANDLE()
    if _SFmpq.SFileOpenArchive(path, priority, flags, byref(f)):
        return f

@debug_log
def SFileCloseArchive(mpq):
    return _SFmpq.SFileCloseArchive(mpq)

@debug_log
def SFileOpenFileEx(mpq, path, search=SFILE_SEARCH_CURRENT_ONLY):
    f = MPQHANDLE()
    if _SFmpq.SFileOpenFileEx(mpq if mpq else None, path, search, byref(f)):
        return f

@debug_log
def SFileCloseFile(ffile):
    return _SFmpq.SFileCloseFile(ffile)

@debug_log
def SFileGetFileSize(ffile, high=False):
    s = c_uint32()
    l = _SFmpq.SFileGetFileSize(ffile, byref(s))
    if high:
        return (l, s.value)
    return l

@debug_log
def SFileReadFile(ffile, read=None):
    aall = read == None
    if aall:
        read = SFileGetFileSize(ffile)
        if read == -1:
            return
    data = create_string_buffer(read)
    r = c_uint32()
    total_read = 0
    while total_read < read:
        if _SFmpq.SFileReadFile(ffile, byref(data, total_read), read - total_read, byref(r), None):
            total_read += r.value
        else:
            return
    return (data.raw[:total_read], total_read)

@debug_log
def SFileSetLocale(locale):
    return _SFmpq.SFileSetLocale(locale)

@debug_log
def SFileGetFileInfo(mpq, flags=SFILE_INFO_BLOCK_SIZE):
    return _SFmpq.SFileGetFileInfo(mpq, flags)

# listfiles is either a list of file lists or a file list itself depending on flags, either are seperated by newlines (\n \r or \r\n?)
@debug_log
def SFileListFiles(mpq, listfiles='', flags=0):
    n = SFileGetFileInfo(mpq, SFILE_INFO_HASH_TABLE_SIZE)
    if n < 1:
        return []
    f = (FILELISTENTRY * n)()
    _SFmpq.SFileListFiles(mpq, listfiles, f, flags)
    return filter(lambda e: e.fileExists, f)

@debug_log
def SFileSetArchivePriority(mpq, priority):
    return _SFmpq.SFileSetArchivePriority(mpq, priority)

@debug_log
def MpqOpenArchiveForUpdate(path, flags=MOAU_OPEN_ALWAYS, maxfiles=1024):
    return _SFmpq.MpqOpenArchiveForUpdate(path, flags, maxfiles)

@debug_log
def MpqCloseUpdatedArchive(handle, unknown=0):
    return _SFmpq.MpqCloseUpdatedArchive(handle, unknown)

@debug_log
def MpqAddFileToArchive(mpq, source, dest, flags=MAFA_REPLACE_EXISTING):
    return _SFmpq.MpqAddFileToArchive(mpq, source, dest, flags)

@debug_log
def MpqAddFileFromBuffer(mpq, vbuffer, ffile, flags=MAFA_REPLACE_EXISTING):
    return _SFmpq.MpqAddFileFromBuffer(mpq, vbuffer, len(vbuffer), ffile, flags)

@debug_log
def MpqCompactArchive(mpq):
    return _SFmpq.MpqCompactArchive(mpq)

@debug_log
def MpqOpenArchiveForUpdateEx(mpq, flags=MOAU_OPEN_ALWAYS, maxfiles=1024, blocksize=3):
    return _SFmpq.MpqOpenArchiveForUpdateEx(mpq, flags, maxfiles, blocksize)

@debug_log
def MpqAddFileToArchiveEx(mpq, source, dest, flags=MAFA_REPLACE_EXISTING, comptype=0, complevel=0):
    return _SFmpq.MpqAddFileToArchiveEx(mpq, source, dest, flags, comptype, complevel)

@debug_log
def MpqRenameAndSetFileLocale(mpq, oldname, newname, oldlocale, newlocale):
    return _SFmpq.MpqRenameAndSetFileLocale(mpq, oldname, newname, oldlocale, newlocale)

@debug_log
def MpqDeleteFileWithLocale(mpq, ffile, locale):
    return _SFmpq.MpqDeleteFileWithLocale(mpq, ffile, locale)

@debug_log
def MpqSetFileLocale(mpq, ffile, oldlocale, newlocale):
    return _SFmpq.MpqSetFileLocale(mpq, ffile, oldlocale, newlocale)

try:
    if __name__ == '__main__':
        work();
except KeyboardInterrupt:
    exit(4);
