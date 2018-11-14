from patterns import *
from os.path import join
from os.path import exists
from os.path import islink

import os
import codecs

class Struct(object):
    pass


class Generator(object):
    def __init__(self, db):
        self.db = db
        self.by_instruction = {}
        for entry in self.db.entries:
            if entry.instructions is None:
                continue

            for instr, _ in entry.instructions:
                if instr not in self.by_instruction:
                    self.by_instruction[instr] = [entry]
                else:
                    self.by_instruction[instr].append(entry)

    
    def generate(self, targetdir):
        self.generate_man_pages(targetdir)
        self.generate_links(targetdir)


    def generate_man_pages(self, targetdir):
        for i, entry in enumerate(self.db.entries):
            path = join(targetdir, entry.name) + '.' + MAN_GROUP
            if exists(path):
                #raise RuntimeError("'%s' already exists, won't continue" % path)
                pass

            print("Generating %s (%d of %d)" % (path, i+1, len(self.db)))
            text = self.generate_man_page(entry)
            with codecs.open(path, 'wt', encoding='utf-8') as f:
                f.write(text)
        else:
            print("Done")


    def generate_man_page(self, entry):
        data = {}
        data['group']       = MAN_GROUP
        data['date']        = self.db.date
        data['version']     = self.db.version

        data['technology']  = entry.technology
        data['name']        = entry.name
        data['include']     = entry.include
        data['rettype']     = entry.rettype
        data['arguments']   = entry.arguments
        data['description'] = entry.description
        data['operation']   = entry.operation

        res = MAIN % data

        if not entry.instructions:
            res += NO_INSTRUCTION_NOTE

        if entry.categories:
            tmp = [CATEGORY_ENTRY % item for item in entry.categories]
            res += CATEGORY_HEADER % (', '.join(tmp))

        if entry.has_round_note:
            res += ROUND_NOTE

        if entry.operation is not None:
            res += OPERATION % data

        if entry.instructions:
            res += INSTRUCTION_HEADER
            for instr, args in entry.instructions:
                tmp = {
                    'instruction': instr,
                    'arguments'  : args,
                }
                res += INSTRUCTION_ENTRY % tmp
            res += INSTRUCTION_TAIL

        if entry.cpuid:
            res += CPUID_HEADER
            for flag in entry.cpuid:
                tmp = {
                    'flag': flag,
                    'last': '',
                }
                res += CPUID_ENTRY % tmp

        see_also = self.see_also(entry)
        if see_also:
            res += SEE_ALSO_HEADER
            for i, name in enumerate(see_also):
                if i + 1 < len(see_also):
                    last = ','
                else:
                    last = ''

                tmp = {'name': name, 'group': MAN_GROUP, 'last': last}
                res += SEE_ALSO_ENTRY % tmp

        return res

    
    def generate_links(self, targetdir):
        for instruction, entries in self.by_instruction.iteritems():
            target = join(targetdir, instruction) + '.' + MAN_GROUP
            source = entries[0].name + '.' + MAN_GROUP
            if exists(target):
                if islink(target):
                    os.unlink(target)
                else:
                    raise RuntimeError("'%s' already exists and is not a symlink" % target)

            os.symlink(source, target)


    def see_also(self, entry):
        s = Struct()
        s.list = []

        def get_entries(instruction):
            try:
                s.list.extend(self.by_instruction[instruction])
            except KeyError:
                pass

        for instr, _ in entry.instructions:
            get_entries(instr)

            if instr.startswith('p') or instr.startswith('vp'):
                # integer instructions

                get_entries('vp' + instr[1:]) # try match pshufb [SSE] with vpshufb [AVX]
                get_entries('v'  + instr[2:]) # or vice-versa

            elif instr.endswith('ps') or instr.endswith('pd') or instr.endswith('ss'):
                # floating point instructions
                get_entries(instr[:-2] + 'pd') # addXX -> addpd
                get_entries(instr[:-2] + 'ps') # addXX -> addpd
                get_entries(instr[:-2] + 'ss') # addXX -> addss

                if instr.startswith('v'):
                    get_entries(instr[1:-2] + 'pd') # vaddXX -> addpd
                    get_entries(instr[1:-2] + 'ps') # vaddXX -> addpd
                    get_entries(instr[1:-2] + 'ss') # vaddXX -> addss
                else:
                    get_entries('v' + instr[:-2] + 'pd') # addXX -> vaddpd
                    get_entries('v' + instr[:-2] + 'ps') # addXX -> vaddpd
                    get_entries('v' + instr[:-2] + 'ss') # addXX -> vaddss


        if len(s.list) <= 1:
            return

        list = sorted(set(s.list))

        return [item.name for item in list if item.name != entry.name]

