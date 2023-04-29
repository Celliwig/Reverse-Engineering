import sys

# Carry store
carry=0

def addc(val1, val2, valcar):
    global carry
    tmpval=val1+val2+valcar
    carry=0
    if (tmpval&0xf0000)>0:
       carry=1
    return tmpval&0xffff

def add(val1, val2):
    return addc(val1, val2, 0)

# Initial values
ax=int(sys.argv[1], base=16)
dx=0x4324
addax=int(sys.argv[2], base=16)

# Calcs
ax&=0x0fff
ax=add(ax, ax)
dx=addc(dx, dx, carry)
ax=addc(ax, ax, carry)
dx=addc(dx, dx, carry)
ax=addc(ax, ax, carry)
dx=addc(dx, dx, carry)
ax=addc(ax, ax, carry)
dx=addc(dx, dx, carry)
ax=addc(ax, ax, carry)
# xchg ax, dx
tmpval=dx
dx=ax
ax=tmpval
dx&=0x000f
ax=add(ax, addax)
dx=addc(dx, 0, carry)

print("AX=0x%x DX=0x%x" % (ax, dx))
