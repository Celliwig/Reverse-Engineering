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
Initial analysis (aaaa) in radare identifies a number of functions with only the entry point and main function being labeled (which is not surprising). A good place to start when trying to disassemble a program is the user I/O and this is where things started to become interesting. As this is a DOS program it would be expected that the program would use INT 10h to print information to the screen. Searching the program code for '0xcd 0x10' (INT 10h instruction) doesn't produce many results, so the debug commands step over ('p') and step into ('t') were used to identify a section of code that updated the screen. After a few attempts a block was identified that among other things cleared the screen (partial listing from radare below):

<div style="height: 400px; overflow: auto;"><table height="400px" border=0><tr><td>
<code>
            ; CALL XREF from fcn.00001476 @ 0x147d(x)
            ; CALL XREF from fcn.000019b4 @ 0x19c3(x)
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

<div style="height: 400px; overflow: auto;"><table height="400px" border=0><tr><td>
<code>
</code>
</td></tr></table></div>

##ROM access code


## References
1. https://www.seabios.org/SeaBIOS
2. https://www.tianocore.org/
3. https://www.linuxboot.org/
4. https://www.freedos.org/


