import uniasm
from binascii import hexlify

assembler = uniasm.Assembler()

REGISTER_CTX_GLOBAL  = '000'
REGISTER_CTX_CURRENT = '001'
REGISTER_CTX_TASK0   = '010'
REGISTER_CTX_TASK1   = '011'
REGISTER_CTX_TASK2   = '100'
REGISTER_CTX_TASK3   = '101'

REGISTER_TYPE_STATUS   = '00'
REGISTER_TYPE_LOCALGPR   = '01'
REGISTER_TYPE_GLOBALEXC  = '01'
REGISTER_TYPE_LOCALMMAP     = '10'
REGISTER_TYPE_GLOBALSYSCALL = '10'
REGISTER_TYPE_LOCAL_IOMAP = '11'

REGISTER_SPEC0 = '000'
REGISTER_SPEC1 = '001'
REGISTER_SPEC2 = '010'
REGISTER_SPEC3 = '011'
REGISTER_SPEC4 = '100'
REGISTER_SPEC5 = '101'
REGISTER_SPEC6 = '110'
REGISTER_SPEC7 = '111'

OPCODE_REGLOAD  = 0x01
OPCODE_REGSAVE  = 0x02
OPCODE_COPYBANK = 0x03


def make_regid(reg_ctx,reg_type,reg_specific):
    retval = '0b%s%s%s' % (reg_ctx,reg_type,reg_specific)
    return int(retval,2)

# setup global registers first
assembler.add_reg('GSTATUS',  make_regid(REGISTER_CTX_GLOBAL,REGISTER_TYPE_STATUS,REGISTER_SPEC0),32)    # global status
assembler.add_reg('EXCEPTION',make_regid(REGISTER_CTX_GLOBAL,REGISTER_TYPE_GLOBALEXC,REGISTER_SPEC0),32) # exception handler
assembler.add_reg('SYSCALL',  make_regid(REGISTER_CTX_GLOBAL,REGISTER_TYPE_GLOBALSYSCALL,REGISTER_SPEC0),32)   # syscall handler

# now setup per task registers
for task in [('',REGISTER_CTX_CURRENT),('T0',REGISTER_CTX_TASK0,),('T1',REGISTER_CTX_TASK1),('T2',REGISTER_CTX_TASK2),('T3',REGISTER_CTX_TASK3)]:
    assembler.add_reg('%sSTATUS' % task[0],make_regid(task[1],REGISTER_TYPE_STATUS,REGISTER_SPEC0),32)
    for reg_type in [('GPR',REGISTER_TYPE_LOCALGPR),('MMAP',REGISTER_TYPE_LOCALMMAP),('IOMAP',REGISTER_TYPE_LOCAL_IOMAP)]:
        assembler.add_reg('%s%s0' % (task[0],reg_type[0]), make_regid(task[1],reg_type[1],REGISTER_SPEC0),32)
        assembler.add_reg('%s%s1' % (task[0],reg_type[0]), make_regid(task[1],reg_type[1],REGISTER_SPEC1),32)
        assembler.add_reg('%s%s2' % (task[0],reg_type[0]), make_regid(task[1],reg_type[1],REGISTER_SPEC2),32)
        assembler.add_reg('%s%s3' % (task[0],reg_type[0]), make_regid(task[1],reg_type[1],REGISTER_SPEC3),32)
        assembler.add_reg('%s%s4' % (task[0],reg_type[0]), make_regid(task[1],reg_type[1],REGISTER_SPEC4),32)
        assembler.add_reg('%s%s5' % (task[0],reg_type[0]), make_regid(task[1],reg_type[1],REGISTER_SPEC5),32)
        assembler.add_reg('%s%s6' % (task[0],reg_type[0]), make_regid(task[1],reg_type[1],REGISTER_SPEC6),32)
        assembler.add_reg('%s%s7' % (task[0],reg_type[0]), make_regid(task[1],reg_type[1],REGISTER_SPEC7),32)

def encode_copybank(src_bank,dst_bank,offset):
    retval  = ''
    retval += chr(OPCODE_COPYBANK)
    src_bits = format(src_bank[1], '#004b')
    dst_bits = format(dst_bank[1], '#004b')
    offset_bits = format(offset[1], '#016b')
    retval += uniasm.assemble_bits(src_bits,dst_bits,offset_bits)
    return retval

def encode_mapbank(task_id,virtual_bank,physical_bank):
    # this is not actually a real opcode, it's OPCODE_REGSAVE so we can assign stuff in global registers
    # basically to do a MAPBANK we just update the mmap register for the specific task
    reg_ctx = {0:REGISTER_CTX_TASK0,
               1:REGISTER_CTX_TASK1,
               2:REGISTER_CTX_TASK2,
               3:REGISTER_CTX_TASK3}[task_id[1]]
    reg_id = make_regid(reg_ctx,REGISTER_TYPE_LOCALMMAP,virtual_bank[1])

    # now we need to assemble the new contents for the mmap register - see pegasus_docs/new_isa.txt
    new_mmap = uniasm.assemble_bits('0'*16,                        # 16-bits reserved
                                    '0'*4,                         # 4 bits reserved
                                    '0001',                        # default permissions 0 on all, but bank present
                                     format(physical_bank[1],'#008b')) # physical bank
   
    # now let's assemble the actual code
    retval  = ''
    retval += chr(OPCODE_REGLOAD)
    retval += uniasm.assemble_bits(format(reg_id,'#008b'),   # register ID
                                   '00',                     # overwrite and do not zero extend
                                   '000',                    # set whole register
                                   '010')                    # set from literal 32-bit
    retval += new_mmap # the new mmap value
    return retval

# read pegassus_docs/instruction_set.txt for details on this stuff

assembler.add_opcode('COPYBANK',[uniasm.Operand(from_reg=False,from_literal=True,bitlength=4),   # source bank
                                 uniasm.Operand(from_reg=False,from_literal=True,bitlength=4),   # destination bank
                                 uniasm.Operand(from_reg=False,from_literal=True,bitlength=16)], # address offset
                                 encoder_func=encode_copybank)

assembler.add_opcode('MAPBANK',[uniasm.Operand(from_reg=False,from_literal=True,bitlength=4),    # which task are we messing with?
                                uniasm.Operand(from_reg=False,from_literal=True,bitlength=4),    # which virtual bank are we setting up?
                                uniasm.Operand(from_reg=False,from_literal=True,bitlength=8)],   # which physical bank do we want to assign to it?
                                encoder_func=encode_mapbank)

def do_line(l):
    print '"%s"  =>  0x%s' % (l,hexlify(assembler.assemble_line(l)))

do_line('COPYBANK 0 1 20')
do_line('MAPBANK  0 0 1')
