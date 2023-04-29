# Acer 8730g

Examining the flash ROM write protection scheme implemented on the Acer 8730g laptop.

## Preface
Having suffered a hardware failure on one of my laptops, I dug out a spare which had been collecting dust for some years. This machine had actually been donated to me, but instead of finding it a good home as usual I've hung on to it as it has a decent keyboard/screen/memory configuration and the CPU is okay for the period (note: the disk in it is terrible however even for the period, a slow 5k, there are 2 SATA ports so a spare SSD has helped).

One installation of Debian later and a little configuration, the majority of the hardware is working. The advantage of such an old machine is that nearly all the hardware will have had drivers developed by now! :grin: One problem however is that having received this machine so late in it's life it hadn't had any firmware updates. A major pain when using x86 machines (Intel/AMD) is their dependence on the Management Engine (ME, or it's AMD equivalent), it along with other technologies (eg: Intel AMT) provide a fertile ground for those wishing to compromise machines. Once you hit the OEM EOL for a system you are stuck between a rock and hard place in regard to firmware issues. You can have a perfectly functional machine which is a potential security risk due to ageing firmware, and due to the locked down nature of the ME/bootstrap process, left without means to even replace it. There does exist however a few programs which can help in this situation by disabling different aspects of ME (for earlier versions at least), and there are various ways of improving the security of the main firmware (BIOS/(U)EFI) by replacing (aspects) of it with OSS replacements[1][2][3].

Having previously modified a BayTrail tablet's ROM to lobotomise ME, I wanted to experiment with changing the firmware on this machine. In that case modifing the ROM was easy as it was on a daughterboard that could be detached from the mainboard and hooked up to a SPI programmer to read & write the contents. In this case the ROM is on the mainboard which makes programming in system programming more difficult (plus the machine's a pain to disassemble as well), so programming in situ via software is preferable (obviously still need to factor in the case of having to unbrick it manually :wink: ).

The starting point for this is previously released firmware versions, and visiting Acer's website I was disappointed to find that there were no firmware images available for download. Windows 7 drivers yes, firmware no, thanks a bunch Acer. This left the distasteful option of third party sites, where you have absolutely no assurance of the integrity of the file you're trying to download. I managed to find version 1.09 (same as the system), but with no assurance of what it actually was there was no way it was going anywhere near the system. With this in mind and a wish to be able to update the flash ROM from Linux it's time to roll up the sleeve's and peek (or poke, sorry BASIC joke) under the hood.

## Setup
The firmware update comes packaged as a zipfile, so after unpacking it a number of different files are apparent. The update contains software to flash the ROM in both DOS & Windows, and a couple of different ROM images which differ in that one has an additional data section appended to it. Having a DOS executable (**phlash16.exe**) to analyse was handy as the amount of code dedicated to the interface is minimised (generally) so this was selected as the point of attack. 

#### QEMU/FreeDOS
<img src="pics/qemu-1st-run.png" height="33%" width="33%" align="right">
Static analyse can provide insights into the code, but running a binary can provide greater information far faster, so I decided to use QEMU to provide a virtual environment running FreeDOS[4]. With FreeDOS installed and the binary/ROM transfered a test run could be done. The phlash16 program provides a number of different <a href="phlash16-1.6.9.7.exe/phlash16-args.txt">arguments</a> which can be passed to it, and the required parameters can be found in the batch file 'BIOS.bat'. These are 'phlash16 /x /s /c /mode=3 <bios image>'. Running this produces some output which is not exactly useful but is a good start.
<br clear="right"/><br/>

<img src="pics/qemu-debug-example.png" height="33%" width="33%" align="left">Originally I had been intending to use gdb as the debugger to interrogate phlash16, as QEMU/gdb are designed to work together. Unfortunately they are designed to work together when QEMU is operating in 32bit mode, not in real mode, this causes the disassembler to incorrectly interprete instructions which is no use. Switching gdb to 16bit mode causes a protocol error with QEMU, and while some people do appear to have worked around the problem, I had no luck. Scratching my head for a little while I remembered 'debug' which is a command line debugger that has been included in MS-DOS since version 1.00. An extended version is included in FreeDOS, so loading up the phlash16 executable with this provides a simple TUI to examine the program.
<br clear="left"/>

#### Radare2
<img src="pics/radare2-phlash16-entry0.png" height="33%" width="33%" align="right">
So examining the executable with debug is useful and informative, but to get a better understanding of a program my preferred IDA is radare2. It's has it's flaws but it's OSS, which I much prefer to use when possible. It's built on ncurses so is a TUI rather than a GUI (though there is the 'iaito' Qt frontend), with my main complaint of it being that learning the controls is a bit esoteric. On this particular project there is also another problem however in that the address handling is a little borked. Addresses are displayed as realmode 'segment:offset', but any commands use the actual physical address. Worse still, it also has problems handling the call/jmp instructions (as opposed to lcall/ljmp), where it calculates the address to be always in the first segment, and tracing through the code becomes confusing if you don't notice where you've jumped to. :wink: Lastly is project management where radare2 saves it's state to a git repo. which in theory sounds like a good idea, however as this state is monolithic it becomes quite hard to check changes that have been made (especially if you mistype addresses!). You can however load in configuration from plain text files which is what I tend to do.

<br clear="right"/><br/>

## Phlash16
Initial analysis (aaaa) in radare identifies a number of functions with only the entry point and main function being labeled (which is not surprising). A good place to start when trying to understand a program is the user I/O and this is where things started to become interesting. 

#### Obfuscation (Part 1)
As this is a DOS program it would be expected that the program would use INT 10h to print information to the screen. Searching the program code for '0xcd 0x10' (INT 10h instruction) doesn't produce many results, so the debug commands step over ('p') and step into ('t') were used to identify a section of code that updated the screen. After a few attempts a block was identified that among other things cleared the screen (listing from radare below):

<div style="height: 400px; overflow: auto;"><table height="400px" border=0><tr><td>
<code>
┌ 427: fcn.0000a6d6 ();
│           ; var int16_t var_eh @ bp-0xe
│           ; var uint32_t var_19h @ bp-0x19
│           ; var uint32_t var_1ah @ bp-0x1a
│           ; var uint32_t var_1ch @ bp-0x1c
│           0000:a6d6      c81e0000       enter 0x1e, 0
│           0000:a6da      33db           xor bx, bx
│           0000:a6dc      8ec3           mov es, bx
│           0000:a6de      6626833e4000.  cmp dword es:[0x40], 0
│           0000:a6e5      7505           jne 0xa6ec
│           ; CODE XREFS from fcn.0000a6d6 @ 0xa78b(x), 0xa7bd(x), 0xa801(x)
│           0000:a6e7      33c0           xor ax, ax
│           0000:a6e9      c9             leave
│           0000:a6ea      cb             retf
            0000:a6eb      90             nop
│           ; CODE XREF from fcn.0000a6d6 @ 0xa6e5(x)
│           0000:a6ec      66c746f20012.  mov dword [var_eh], 0x55101200 ; [0x55101200:4]=-1
│           0000:a6f4      8d46e4         lea ax, [var_1ch]
│           0000:a6f7      16             push ss
│           0000:a6f8      50             push ax
│           0000:a6f9      8d4ef2         lea cx, [var_eh]
│           0000:a6fc      16             push ss
│           0000:a6fd      51             push cx
│           0000:a6fe      6a10           push 0x10
│           0000:a700      9a805c1213     lcall fcn.00018da0           ; RELOC 16 
│           0000:a705      83c40a         add sp, 0xa
│           0000:a708      807ee755       cmp byte [var_19h], 0x55     ; 'U'
│           0000:a70c      0f85d400       jne 0xa7e4
│           0000:a710      c746f20300     mov word [var_eh], 3
│           0000:a715      8d46e4         lea ax, [var_1ch]
│           0000:a718      16             push ss
│           0000:a719      50             push ax
│           0000:a71a      8d4ef2         lea cx, [var_eh]
│           0000:a71d      16             push ss
│           0000:a71e      51             push cx
│           0000:a71f      6a10           push 0x10
│           0000:a721      9a805c1213     lcall fcn.00018da0           ; RELOC 16 
│           0000:a726      83c40a         add sp, 0xa
│           0000:a729      c746f2000f     mov word [var_eh], 0xf00     ; [0xf00:2]=0x681e
│           0000:a72e      8d46e4         lea ax, [var_1ch]
│           0000:a731      16             push ss
│           0000:a732      50             push ax
│           0000:a733      8d4ef2         lea cx, [var_eh]
│           0000:a736      16             push ss
│           0000:a737      51             push cx
│           ; CODE XREFS from section.seg_012 @ +0x17b1(x), +0x17d9(x), +0x17e1(x)
│           0000:a738      6a10           push 0x10
│           0000:a73a      9a805c1213     lcall fcn.00018da0           ; RELOC 16 
│           0000:a73f      83c40a         add sp, 0xa
│           0000:a742      8a46e4         mov al, byte [var_1ch]
│           0000:a745      2ae4           sub ah, ah
│           0000:a747      48             dec ax
│           0000:a748      48             dec ax
│           0000:a749      7455           je 0xa7a0
│           0000:a74b      48             dec ax
│           0000:a74c      0f848800       je 0xa7d8
│           0000:a750      2d0400         sub ax, 4
│           ; CODE XREF from section.seg_012 @ +0x17a5(x)
│           0000:a753      743a           je 0xa78f
│           0000:a755      c746f20700     mov word [var_eh], 7
│           0000:a75a      8d46e4         lea ax, [var_1ch]
│           ; CODE XREF from section.seg_012 @ +0x17a9(x)
│           0000:a75d      16             push ss
│           0000:a75e      50             push ax
│           0000:a75f      8d4ef2         lea cx, [var_eh]
│           0000:a762      16             push ss
│           ; CODE XREFS from section.seg_012 @ +0x1752(x), +0x17cb(x)
│           0000:a763      51             push cx
│           0000:a764      6a10           push 0x10
│           0000:a766      9a805c1213     lcall fcn.00018da0           ; RELOC 16 
│           0000:a76b      83c40a         add sp, 0xa
│           0000:a76e      c746f2000f     mov word [var_eh], 0xf00     ; [0xf00:2]=0x681e
│           0000:a773      8d46e4         lea ax, [var_1ch]
│           0000:a776      16             push ss
│           0000:a777      50             push ax
│           ; CODE XREFS from section.seg_012 @ +0x174f(x), +0x1813(x), +0x182c(x)
│           0000:a778      8d4ef2         lea cx, [var_eh]
│           0000:a77b      16             push ss
│           0000:a77c      51             push cx
│           0000:a77d      6a10           push 0x10
│           0000:a77f      9a805c1213     lcall fcn.00018da0           ; RELOC 16 
│           0000:a784      83c40a         add sp, 0xa
│           0000:a787      807ee407       cmp byte [var_1ch], 7
│           0000:a78b      0f8558ff       jne 0xa6e7
│           ; CODE XREF from fcn.0000a6d6 @ 0xa753(x)
│           0000:a78f      66c7062e3b00.  mov dword [0x3b2e], 0xb0000000 ; [0x3b2e:4]=0x1312089e
│           0000:a798      c7064673b403   mov word [0x7346], 0x3b4     ; [0x7346:2]=0xb49a
│           0000:a79e      eb33           jmp 0xa7d3
│           ; CODE XREF from fcn.0000a6d6 @ 0xa749(x)
│           0000:a7a0      c746f20152     mov word [var_eh], 0x5201    ; [0x5201:2]=0x9a05
│           0000:a7a5      8d46e4         lea ax, [var_1ch]
│           0000:a7a8      16             push ss
│           ; CODE XREF from section.seg_012 @ +0x17f6(x)
│           0000:a7a9      50             push ax
│           0000:a7aa      8d46f2         lea ax, [var_eh]
│           0000:a7ad      16             push ss
│           0000:a7ae      50             push ax
│           0000:a7af      6a10           push 0x10
│           0000:a7b1      9a805c1213     lcall fcn.00018da0           ; RELOC 16 
│           0000:a7b6      83c40a         add sp, 0xa
│           0000:a7b9      837ee600       cmp word [var_1ah], 0
│           0000:a7bd      0f8426ff       je 0xa6e7
│           0000:a7c1      8b46e6         mov ax, word [var_1ah]
│           0000:a7c4      c7062e3b0000   mov word [0x3b2e], 0         ; [0x3b2e:2]=0x89e
│           0000:a7ca      a3303b         mov word [0x3b30], ax        ; [0x3b30:2]=0x1312
│           ; CODE XREF from fcn.0000a6d6 @ 0xa7e1(x)
│           0000:a7cd      c7064673d403   mov word [0x7346], 0x3d4     ; [0x7346:2]=0xb49a
│           ; CODE XREFS from fcn.0000a6d6 @ 0xa79e(x), 0xa881(x)
│           0000:a7d3      b8ffff         mov ax, 0xffff
│           ; CODE XREFS from section.seg_012 @ +0x1851(x), +0x185f(x)
│           0000:a7d6      c9             leave
│           0000:a7d7      cb             retf
│           ; CODE XREF from fcn.0000a6d6 @ 0xa74c(x)
│           0000:a7d8      66c7062e3b00.  mov dword [0x3b2e], 0xb8000000 ; [0x3b2e:4]=0x1312089e
│           0000:a7e1      ebea           jmp 0xa7cd
            0000:a7e3      90             nop
│           ; CODE XREF from fcn.0000a6d6 @ 0xa70c(x)
│           0000:a7e4      c746f2001a     mov word [var_eh], 0x1a00    ; [0x1a00:2]=0x1215
│           0000:a7e9      8d46e4         lea ax, [var_1ch]
│           0000:a7ec      16             push ss
│           0000:a7ed      50             push ax
│           0000:a7ee      8d4ef2         lea cx, [var_eh]
│           0000:a7f1      16             push ss
│           0000:a7f2      51             push cx
│           0000:a7f3      6a10           push 0x10
│           0000:a7f5      9a805c1213     lcall fcn.00018da0           ; RELOC 16 
│           0000:a7fa      83c40a         add sp, 0xa
│           ; CODE XREF from section.seg_012 @ +0x188e(x)
│           0000:a7fd      807ee41a       cmp byte [var_1ch], 0x1a
│           0000:a801      0f85e2fe       jne 0xa6e7
│           0000:a805      f606840108     test byte [0x184], 8         ; [0x184:1]=80
│           0000:a80a      7519           jne 0xa825
│           0000:a80c      c746f20300     mov word [var_eh], 3
│           0000:a811      8d46e4         lea ax, [var_1ch]
│           0000:a814      16             push ss
│           0000:a815      50             push ax
│           0000:a816      8d46f2         lea ax, [var_eh]
│           0000:a819      16             push ss
│           0000:a81a      50             push ax
│           0000:a81b      6a10           push 0x10
│           0000:a81d      9a805c1213     lcall fcn.00018da0           ; RELOC 16 
│           0000:a822      83c40a         add sp, 0xa
│           ; CODE XREF from fcn.0000a6d6 @ 0xa80a(x)
│           0000:a825      c746f2000f     mov word [var_eh], 0xf00     ; [0xf00:2]=0x681e
│           0000:a82a      8d46e4         lea ax, [var_1ch]
│           0000:a82d      16             push ss
│           0000:a82e      50             push ax
│           0000:a82f      8d4ef2         lea cx, [var_eh]
│           0000:a832      16             push ss
│           0000:a833      51             push cx
│           0000:a834      6a10           push 0x10
│           0000:a836      9a805c1213     lcall fcn.00018da0           ; RELOC 16 
│           0000:a83b      83c40a         add sp, 0xa
│           0000:a83e      807ee403       cmp byte [var_1ch], 3
│           0000:a842      7512           jne 0xa856
│           0000:a844      66c7062e3b00.  mov dword [0x3b2e], 0xb8000000 ; [0x3b2e:4]=0x1312089e
│           0000:a84d      c7064673d403   mov word [0x7346], 0x3d4     ; [0x7346:2]=0xb49a
│           0000:a853      eb10           jmp 0xa865
            0000:a855      90             nop
│           ; CODE XREF from fcn.0000a6d6 @ 0xa842(x)
│           0000:a856      66c7062e3b00.  mov dword [0x3b2e], 0xb0000000 ; [0x3b2e:4]=0x1312089e
│           0000:a85f      c7064673b403   mov word [0x7346], 0x3b4     ; [0x7346:2]=0xb49a
│           ; CODE XREF from fcn.0000a6d6 @ 0xa853(x)
│           0000:a865      66c746f20310.  mov dword [var_eh], 0x1003   ; [0x1003:4]=0xc4830fb6
│           0000:a86d      8d46e4         lea ax, [var_1ch]
│           0000:a870      16             push ss
│           0000:a871      50             push ax
│           0000:a872      8d46f2         lea ax, [var_eh]
│           0000:a875      16             push ss
│           0000:a876      50             push ax
│           0000:a877      6a10           push 0x10
│           0000:a879      9a805c1213     lcall fcn.00018da0           ; RELOC 16 
│           0000:a87e      83c40a         add sp, 0xa
└           0000:a881      e94fff         jmp 0xa7d3
</code>
</td></tr></table></div>

There's no INT instructions throughout the function, it just calls the same function with different parameters, so lets look at that.

<div style="height: 400px; overflow: auto;"><table height="400px" border=0><tr><td>
<code>
┌ 36: fcn.00018da0 (int16_t arg_6h);
│           ; arg int16_t arg_6h @ bp+0x6
│           ; var int16_t var_8h @ bp-0x8
│           ; var int16_t var_9h @ bp-0x9
│           ; var int16_t var_ah @ bp-0xa
│           1000:8da0      55             push bp
│           1000:8da1      8bec           mov bp, sp
│           1000:8da3      56             push si
│           1000:8da4      57             push di
│           1000:8da5      83ec0a         sub sp, 0xa
│           1000:8da8      c646f6cd       mov byte [var_ah], 0xcd      ; [0xcd:1]=131
│           1000:8dac      8b4606         mov ax, word [arg_6h]
│           1000:8daf      8846f7         mov byte [var_9h], al
│           1000:8db2      3c25           cmp al, 0x25                 ; '%'
│           1000:8db4      740a           je 0x8dc0
│           1000:8db6      3c26           cmp al, 0x26                 ; '&'
│           1000:8db8      7406           je 0x8dc0
│           1000:8dba      c646f8cb       mov byte [var_8h], 0xcb      ; [0xcb:1]=18
│           1000:8dbe      eb0c           jmp fcn.00008dcc
            1000:8dc0      c646facb       mov byte [bp - 6], 0xcb      ; [0xcb:1]=18
            1000:8dc4      c646f944       mov byte [bp - 7], 0x44      ; 'D'
                                                                       ; [0x44:1]=104
            1000:8dc8      c646f844       mov byte [bp - 8], 0x44      ; 'D'
                                                                       ; [0x44:1]=104
            1000:8dcc      8c56f4         mov word [bp - 0xc], ss
            1000:8dcf      8d46f6         lea ax, [bp - 0xa]
            1000:8dd2      8946f2         mov word [bp - 0xe], ax
            1000:8dd5      1e             push ds
            1000:8dd6      c57e08         lds di, [bp + 8]
            1000:8dd9      8b05           mov ax, word [di]
            1000:8ddb      8b5d02         mov bx, word [di + 2]
            1000:8dde      8b4d04         mov cx, word [di + 4]
            1000:8de1      8b5506         mov dx, word [di + 6]
            1000:8de4      8b7508         mov si, word [di + 8]
            1000:8de7      8b7d0a         mov di, word [di + 0xa]
            1000:8dea      1f             pop ds
            1000:8deb      55             push bp
            1000:8dec      f8             clc
            1000:8ded      ff5ef2         lcall [bp - 0xe]
            1000:8df0      5d             pop bp
            1000:8df1      fc             cld
            1000:8df2      1e             push ds
            1000:8df3      57             push di
            1000:8df4      c57e0c         lds di, [bp + 0xc]
            1000:8df7      8905           mov word [di], ax
            1000:8df9      895d02         mov word [di + 2], bx
            1000:8dfc      894d04         mov word [di + 4], cx
            1000:8dff      895506         mov word [di + 6], dx
            1000:8e02      897508         mov word [di + 8], si
            1000:8e05      8f450a         pop word [di + 0xa]
            1000:8e08      7204           jb 0x8e0e                    ; fcn.00008e06+0x8
            1000:8e0a      33f6           xor si, si
            1000:8e0c      eb0f           jmp 0x8e1d                   ; fcn.00008e06+0x17
            1000:8e0e      59             pop cx
            1000:8e0f      51             push cx
            1000:8e10      1e             push ds
            1000:8e11      8ed9           mov ds, cx
            1000:8e13      0e             push cs
            1000:8e14      e8cdb7         call fcn.000045e4            ; fcn.000043c8+0x21c
            1000:8e17      1f             pop ds
            1000:8e18      be0100         mov si, 1
            1000:8e1b      8b05           mov ax, word [di]
            1000:8e1d      89750c         mov word [di + 0xc], si
            1000:8e20      1f             pop ds
            1000:8e21      83c40a         add sp, 0xa
            1000:8e24      5f             pop di
            1000:8e25      5e             pop si
            1000:8e26      8be5           mov sp, bp
            1000:8e28      5d             pop bp
            1000:8e29      cb             retf
</code>
</td></tr></table></div>

Still no sign of an INT 10h, so what's going on? Examining the code further:
```
│           1000:8da8      c646f6cd       mov byte [var_ah], 0xcd      ; [0xcd:1]=131
│           1000:8dac      8b4606         mov ax, word [arg_6h]
│           1000:8daf      8846f7         mov byte [var_9h], al
```
The first thing it does is move 0xcd into a memory address, fetch a value from the stack, and pushes the lower portion into the following memory address. I think you can probably guess that at this point AL equals 0x10. A little bit further on it then saves 0xcb (retf) after that. It also creates a jmp address:
```
            1000:8dcc      8c56f4         mov word [bp - 0xc], ss
            1000:8dcf      8d46f6         lea ax, [bp - 0xa]
            1000:8dd2      8946f2         mov word [bp - 0xe], ax
```
Loads any required registers:
```
            1000:8dd9      8b05           mov ax, word [di]
            1000:8ddb      8b5d02         mov bx, word [di + 2]
            1000:8dde      8b4d04         mov cx, word [di + 4]
            1000:8de1      8b5506         mov dx, word [di + 6]
            1000:8de4      8b7508         mov si, word [di + 8]
            1000:8de7      8b7d0a         mov di, word [di + 0xa]
```
Then jumps to the newly created mini-function:
```
            1000:8ded      ff5ef2         lcall [bp - 0xe]
```
So all this is just a way to obfuscate INT calls, so having defined this function it can be seen that the previous one does in fact initialise the screen (among other things). This sets the tone for the analyse of the rest of this binary.

#### I/O Ports
Speaking of tone, in the function that calls initialise screen (which is the 2nd function):
<div style="height: 400px; overflow: auto;"><table height="400px" border=0><tr><td>
<code>
┌ 40: fcn.000019b4 ();
│           0000:19b4      6a56           push 0x56                    ; 'V'
│           0000:19b6      66ff368401     push dword [0x184]
│           0000:19bb      9a98096d0a     lcall fcn.0000b068           ; RELOC 16 
│           0000:19c0      83c406         add sp, 6
│           ; DATA XREF from fcn.000008f3 @ 0x12d5(r)
│           0000:19c3      9a06006d0a     lcall fcn.0000a6d6           ; RELOC 16 
│           0000:19c8      0bc0           or ax, ax
│           0000:19ca      7405           je 0x19d1
│           0000:19cc      800e8d0102     or byte [0x18d], 2
│           ; CODE XREF from fcn.000019b4 @ 0x19ca(x)
│           0000:19d1      6a07           push 7
│           0000:19d3      9a6c0b6d0a     lcall fcn.0000b23c           ; RELOC 16 
│           0000:19d8      83c402         add sp, 2
└           0000:19db      cb             retf
</code>
</td></tr></table></div>

The first one is worth analysing as well:
<div style="height: 400px; overflow: auto;"><table height="400px" border=0><tr><td>
<code>
┌ 278: fcn.0000b068 (int16_t arg_6h, int16_t arg_ah);
│           ; arg int16_t arg_6h @ bp+0x6
│           ; arg int16_t arg_ah @ bp+0xa
│           ; var uint32_t var_2h @ bp-0x2
│           ; var int16_t var_4h @ bp-0x4
│           ; var int16_t var_6h @ bp-0x6
│           0000:b068      c8060000       enter 6, 0
│           0000:b06c      ff760a         push word [arg_ah]
│           0000:b06f      688000         push 0x80
│           0000:b072      9ab45d1213     lcall fcn.00018ed4           ; RELOC 16 
│           0000:b077      83c404         add sp, 4
│           0000:b07a      f6460608       test byte [arg_6h], 8
│           0000:b07e      0f85fa00       jne 0xb17c
│           0000:b082      ff760a         push word [arg_ah]
│           0000:b085      688000         push 0x80
│           0000:b088      9ab45d1213     lcall fcn.00018ed4           ; RELOC 16 
│           0000:b08d      83c404         add sp, 4
│           0000:b090      666a70         push 0x70                    ; 'p'
│           0000:b093      9ab45d1213     lcall fcn.00018ed4           ; RELOC 16 
│           0000:b098      83c404         add sp, 4
│           0000:b09b      6a71           push 0x71                    ; 'q'
│           0000:b09d      9aa65d1213     lcall fcn.00018ec6           ; RELOC 16 
│           0000:b0a2      83c402         add sp, 2
│           0000:b0a5      8846fe         mov byte [var_2h], al
│           0000:b0a8      666870000200   push 0x20070                 ; 'p'
│           0000:b0ae      9ab45d1213     lcall fcn.00018ed4           ; RELOC 16 
│           0000:b0b3      83c404         add sp, 4
│           ; DATA XREF from fcn.000043c8 @ 0x4707(r)
│           ; DATA XREF from fcn.00014778 @ 0x4919(r)
│           0000:b0b6      6a71           push 0x71                    ; 'q'
│           0000:b0b8      9aa65d1213     lcall fcn.00018ec6           ; RELOC 16 
│           0000:b0bd      83c402         add sp, 2
│           0000:b0c0      8846fc         mov byte [var_4h], al
│           0000:b0c3      666870000400   push 0x40070                 ; 'p'
│           0000:b0c9      9ab45d1213     lcall fcn.00018ed4           ; RELOC 16 
│           0000:b0ce      83c404         add sp, 4
│           0000:b0d1      6a71           push 0x71                    ; 'q'
│           0000:b0d3      9aa65d1213     lcall fcn.00018ec6           ; RELOC 16 
│           0000:b0d8      83c402         add sp, 2
│           ; CODE XREF from section.seg_012 @ +0xf69(x)
│           0000:b0db      8846fa         mov byte [var_6h], al
│           0000:b0de      66a18c01       mov eax, dword [0x18c]       ; [0x18c:4]=0x1312089e
│           0000:b0e2      662500800010   and eax, 0x10008000
│           0000:b0e8      660bc0         or eax, eax
│           0000:b0eb      746f           je 0xb15c
│           0000:b0ed      8a460a         mov al, byte [arg_ah]
│           0000:b0f0      2ae4           sub ah, ah
│           0000:b0f2      50             push ax
│           0000:b0f3      8a46fe         mov al, byte [var_2h]
│           0000:b0f6      250f00         and ax, 0xf
│           0000:b0f9      053000         add ax, 0x30
│           0000:b0fc      50             push ax
│           0000:b0fd      8a46fe         mov al, byte [var_2h]
│           0000:b100      c0e804         shr al, 4
│           ; DATA XREF from fcn.000135d7 @ 0x135db(r)
│           ; DATA XREF from fcn.000135d7 @ +0x3a(r)
│           0000:b103      2ae4           sub ah, ah
│           0000:b105      053000         add ax, 0x30
│           0000:b108      50             push ax
│           0000:b109      8a46fc         mov al, byte [var_4h]
│           0000:b10c      250f00         and ax, 0xf
│           0000:b10f      053000         add ax, 0x30
│           0000:b112      50             push ax
│           0000:b113      8a46fc         mov al, byte [var_4h]
│           0000:b116      c0e804         shr al, 4
│           0000:b119      2ae4           sub ah, ah
│           0000:b11b      053000         add ax, 0x30
│           0000:b11e      50             push ax
│           0000:b11f      8a46fa         mov al, byte [var_6h]
│           0000:b122      250f00         and ax, 0xf
│           0000:b125      053000         add ax, 0x30
│           0000:b128      50             push ax
│           ; CODE XREF from section.seg_012 @ +0x21a4(x)
│           0000:b129      8a46fa         mov al, byte [var_6h]
│           0000:b12c      c0e804         shr al, 4
│           0000:b12f      2ae4           sub ah, ah
│           0000:b131      053000         add ax, 0x30                 ; int16_t arg_6h
│           0000:b134      50             push ax
│           0000:b135      1e             push ds
│           0000:b136      68893c         push 0x3c89
│           0000:b139      1e             push ds
│           0000:b13a      68d25c         push 0x5cd2
│           0000:b13d      9a96391213     lcall fcn.00016ab6           ; RELOC 16 
│           0000:b142      83c416         add sp, 0x16
│           0000:b145      1e             push ds
│           0000:b146      68d25c         push 0x5cd2
│           0000:b149      66681f001000   push 0x10001f                ; '\x1f'
│           0000:b14f      666844001800   push 0x180044                ; 'D'
│           0000:b155      0e             push cs
│           0000:b156      e8c7fc         call fcn.0000ae20
│           0000:b159      83c40c         add sp, 0xc
│           ; CODE XREF from fcn.0000b068 @ 0xb0eb(x)
│           0000:b15c      a0642c         mov al, byte [0x2c64]        ; [0x2c64:1]=199
│           0000:b15f      3846fe         cmp byte [var_2h], al
│           0000:b162      7418           je 0xb17c
│           0000:b164      f6460610       test byte [arg_6h], 0x10
│           0000:b168      750c           jne 0xb176
│           0000:b16a      3cff           cmp al, 0xff
│           0000:b16c      7408           je 0xb176
│           0000:b16e      1e             push ds
│           0000:b16f      68a23b         push 0x3ba2
│           0000:b172      0e             push cs
│           0000:b173      e8d603         call fcn.0000b54c
│           ; CODE XREFS from fcn.0000b068 @ 0xb168(x), 0xb16c(x)
│           0000:b176      8a46fe         mov al, byte [var_2h]
│           0000:b179      a2642c         mov byte [0x2c64], al        ; [0x2c64:1]=199
│           ; CODE XREFS from fcn.0000b068 @ 0xb07e(x), 0xb162(x)
│           ; CODE XREFS from section.seg_012 @ +0x21e8(x), +0x21ef(x), +0x21f6(x)
│           0000:b17c      c9             leave
└           0000:b17d      cb             retf
</code>
</td></tr></table></div>

The first two different function calls are obviously for:
```
┌ 14: fcn.00018ed4 (int16_t arg_6h, int16_t arg_8h);
│           1000:8ed4      55             push bp
│           1000:8ed5      8bec           mov bp, sp
│           1000:8ed7      8b5606         mov dx, word [arg_6h]
│           1000:8eda      8a4608         mov al, byte [arg_8h]
│           1000:8edd      ee             out dx, al
│           1000:8ede      b400           mov ah, 0
│           1000:8ee0      5d             pop bp
└           1000:8ee1      cb             retf
```
Writing to an I/O port.
```
┌ 13: fcn.00018ec6 (int16_t arg_6h);
│           1000:8ec6      55             push bp
│           1000:8ec7      8bec           mov bp, sp
│           1000:8ec9      8b5606         mov dx, word [arg_6h]
│           1000:8ecc      ec             in al, dx
│           1000:8ecd      32e4           xor ah, ah
│           1000:8ecf      8be5           mov sp, bp
│           1000:8ed1      5d             pop bp
└           1000:8ed2      cb             retf
```
Reading from an I/O port.

Applying this knowlege to the previous function it can be seen that it's interogating I/O ports 0x70-71 which is RTC, and is infact reading the time (defining the function is helpful because it's call'ed from all over the code). Note that I/O port 0x80 is the BIOS debug port, and if implemented is just a register connected to a hexadecimal LED/LCD display and normally shows POST codes from the firmware at startup.

Also called from this function is this:
<div style="height: 400px; overflow: auto;"><table height="400px" border=0><tr><td>
<code>
┌ 7: fcn.0000b54c (int16_t arg3);
│           ; arg int16_t arg3 @ bx
│           0000:b54c      c8020000       enter 2, 0
└           0000:b550      e98900         jmp 0xb5dc
            0000:b553      90             nop
            ; CODE XREF from fcn.0000b54c @ +0x98(x)
            0000:b554      66684300b600   push 0xb60043                ; 'C'
            0000:b55a      9ab45d1213     lcall fcn.00018ed4           ; RELOC 16 
            0000:b55f      83c404         add sp, 4
            0000:b562      c45e06         les bx, [bp + 6]
            0000:b565      2ae4           sub ah, ah
            0000:b567      268a07         mov al, byte es:[bx]
            0000:b56a      50             push ax
            0000:b56b      6a42           push 0x42                    ; 'B'
            0000:b56d      9ab45d1213     lcall fcn.00018ed4           ; RELOC 16 
            0000:b572      83c404         add sp, 4
            0000:b575      c45e06         les bx, [bp + 6]
            0000:b578      2ae4           sub ah, ah
            0000:b57a      268a4701       mov al, byte es:[bx + 1]
            0000:b57e      50             push ax
            0000:b57f      6a42           push 0x42                    ; 'B'
            0000:b581      9ab45d1213     lcall fcn.00018ed4           ; RELOC 16 
            0000:b586      83c404         add sp, 4
            ; CODE XREF from loc.0001b2df @ +0x26f(x)
            0000:b589      c45e06         les bx, [bp + 6]
            0000:b58c      26833f00       cmp word es:[bx], 0
            0000:b590      7417           je 0xb5a9
            0000:b592      6a61           push 0x61                    ; 'a'
            0000:b594      9aa65d1213     lcall fcn.00018ec6           ; RELOC 16 
            0000:b599      83c402         add sp, 2
            0000:b59c      0c03           or al, 3
            0000:b59e      50             push ax
            0000:b59f      6a61           push 0x61                    ; 'a'
            0000:b5a1      9ab45d1213     lcall fcn.00018ed4           ; RELOC 16 
            0000:b5a6      83c404         add sp, 4
            ; CODE XREF from fcn.0000b54c @ +0x44(x)
            0000:b5a9      c45e06         les bx, [bp + 6]
            0000:b5ac      26ff7702       push word es:[bx + 2]
            0000:b5b0      0e             push cs
            0000:b5b1      e83600         call fcn.0000b5ea
            0000:b5b4      83c402         add sp, 2
            0000:b5b7      c45e06         les bx, [bp + 6]
            0000:b5ba      26833f00       cmp word es:[bx], 0
            0000:b5be      7418           je 0xb5d8
            0000:b5c0      6a61           push 0x61                    ; 'a'
            0000:b5c2      9aa65d1213     lcall fcn.00018ec6           ; RELOC 16 
            0000:b5c7      83c402         add sp, 2
            0000:b5ca      25fc00         and ax, 0xfc
            0000:b5cd      50             push ax
            0000:b5ce      6a61           push 0x61                    ; 'a'
            0000:b5d0      9ab45d1213     lcall fcn.00018ed4           ; RELOC 16 
            0000:b5d5      83c404         add sp, 4
            ; CODE XREF from fcn.0000b54c @ +0x72(x)
            0000:b5d8      83460604       add word [bp + 6], 4
            ; CODE XREF from fcn.0000b54c @ 0xb550(x)
            0000:b5dc      c45e06         les bx, [bp + 6]
            0000:b5df      26837f0200     cmp word es:[bx + 2], 0
            0000:b5e4      0f856cff       jne 0xb554
            0000:b5e8      c9             leave
            0000:b5e9      cb             retf
</code>
</td></tr></table></div>
It's not particularly important, and even potentially annoying. It's writing to I/O ports 0x42-43 which is the PIT (Programmable Interval Timer), and port 0x61 which is the KBC (KeyBoard Controller). What do these things have in common? The PC speaker. The PIT generates the tone, and there's a gate in the KBC which enables the PIT to drive the PC speaker. The 'call fcn.0000b5ea' is a jump to a time delay which sets the interval of the beep.

#### QEMU options
The function is not needed (phlash even has a parameter to disable it), but I (briefly) thought it'd be nice to have QEMU output the beep which it does support. Adding the arguements '-audiodev alsa,id=default -machine pcspk-audiodev=default' to QEMU's command line parameters rewards you with the PC speaker on your sound card.

While this option is not particularly needed, even wanted, a more helpful option came to light while reading QEMU's manpage. The VGA display is, by default, routed to an SDL backed window which provides the system monitor. There is an option available, '-display curses', which instead renders the VGA display using the (n)curses library. Obviously this useless for a graphical mode where it'll display nothing, but handy when the system is in text mode as here. Specifically with the debugger you can select and copy data from the text display which makes note taking far quicker!


##ROM access code


## References
1. https://www.seabios.org/SeaBIOS
2. https://www.tianocore.org/
3. https://www.linuxboot.org/
4. https://www.freedos.org/


